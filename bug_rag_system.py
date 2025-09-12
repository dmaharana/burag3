import psycopg2
import numpy as np
from typing import Dict, List,Optional,Tuple
from openai import OpenAI, api_key
from constants import EMBEDDING_DIMENSION
import logging
from datetime import date
from datetime import datetime
from dataclasses import dataclass
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Any
'''
The @dataclass Decorator

The @dataclass decorator is used to automatically generate special methods for the class, 
'''
@dataclass
class BugData:
    incident_number: str
    product: str
    description: str
    closing_notes: str
    resolution_tier_1: str
    resolution_tier_2: str
    resolution_tier_3: str
    problem_id: str
    sys_created_on: datetime
    sys_created_by: str
    priority: int

@dataclass
class IncidentSummary:
    count:int
    incident_numbers:List[str]
    created_by_users:List[str]
    priority:List[int]
    solutions:List[str]
    incidents:List[Dict[str,Any]]

class BugRagSystem:

    def __init__(self,db_config:Dict[str,str],llm_api_url:str="http://localhost:11434", embedding_model:str = "nomic-embed-text:latest"):
        self.db_config = db_config
        self.llm_api_url = llm_api_url
        self.embedding_model = embedding_model
        self.embedding_dimension = EMBEDDING_DIMENSION

    def get_db_connection(self):
        '''Get databse connection'''
        return psycopg2.connect(**self.db_config)

    def generate_embedding(self,text:str) -> List[float]:
        # generate embedding for given text using OpenAI API
        try:
            client = OpenAI(
                base_url=f'{self.llm_api_url}/v1',
                api_key='ollama'
            )

            response = client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            print(f"Embedding model: {self.embedding_model}")
            logging.info(f"Generated embedding for text: {text}, of length: {len(response.data[0].embedding)}")
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Error in generating embedding:{e}")
            return None


    # Get incidents created in last week (with detailed records)

    def get_incidents_by_days(self, days: int) -> IncidentSummary:
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT incident_number, product, description, closing_notes,
                            resolution_tier_1, resolution_tier_2, resolution_tier_3,
                            problem_id, sys_created_on, sys_created_by,priority,
                            CASE priority
                                WHEN 4 THEN 'Critical'
                                WHEN 3 THEN 'High'
                                WHEN 2 THEN 'Medium'
                                WHEN 1 THEN 'Low'
                                ELSE 'Unknown'
                            END AS priority_level
                    FROM bugs
                    WHERE sys_created_on >= NOW() - INTERVAL '1 day' * %s
                    AND sys_created_on <= NOW()
                    ORDER BY sys_created_on DESC
                """
                logging.info(f"Executing query: {query}")
                logging.info(f"Executing query with days: {days}")
                cursor.execute(query, (days,))
                incidents = cursor.fetchall()
                cutoff = date.today() - timedelta(days=days)
                filtered = []
                users = set()
                solutions = set()
                priority_values = []
                for incident in incidents:
                    sys_created_on = incident['sys_created_on']
                    priority = incident['priority']
                    if hasattr(sys_created_on, 'year'):
                        if date(sys_created_on.year, sys_created_on.month, sys_created_on.day) >= cutoff:
                            filtered.append(incident)
                            users.add(incident.get('sys_created_by'))
                            solution = incident.get('closing_notes') or ''
                            if solution:
                                solutions.add(solution)
                            priority_values.append(incident['priority'])

                incident_numbers = [incident['incident_number'] for incident in filtered]
                count = len(incident_numbers)
                return IncidentSummary(
                    count=count,
                    incident_numbers=incident_numbers,
                    created_by_users=list(users),
                    priority=priority_values,
                    solutions=list(solutions),
                    incidents=filtered,
                )

    def store_bug(self, bug_data: BugData) -> int:
        logging.info(f"Storing bug data: {bug_data}")
        # Store bug data and embedding vectors
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Insert bug data
                insert_bug_query = """
                    INSERT INTO bugs(
                        incident_number,
                        product,
                        description,
                        closing_notes,
                        resolution_tier_1,
                        resolution_tier_2,
                        resolution_tier_3,
                        problem_id,
                        sys_created_on,
                        sys_created_by,
                        priority
                    )
                    VALUES(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                """
                cursor.execute(insert_bug_query, (
                    bug_data.incident_number,
                    bug_data.product,
                    bug_data.description,
                    bug_data.closing_notes,
                    bug_data.resolution_tier_1,
                    bug_data.resolution_tier_2,
                    bug_data.resolution_tier_3,
                    bug_data.problem_id,
                    bug_data.sys_created_on,
                    bug_data.sys_created_by,
                    bug_data.priority
                ))
                bug_id = cursor.fetchone()[0]
                logging.info(f"Stored bug data with id: {bug_id}")
                
                # Generate and store embeddings
                self._store_embeddings(cursor, bug_id, bug_data)
                conn.commit()
                return bug_id

    def _store_embeddings(self,cursor,bug_id:int,bug_data:BugData):

        #generate and store different embeddings
        embedding_configs = [
            ("description",bug_data.description),
        ]
        #add closing_notes embedding with resolution_tiers
        if bug_data.closing_notes:
            resolution_text = f"Resolution:{bug_data.closing_notes}"
            if bug_data.resolution_tier_1:
                resolution_text += f" | Tier 1:{bug_data.resolution_tier_1}"
            if bug_data.resolution_tier_2:
                resolution_text += f" | Tier 2:{bug_data.resolution_tier_2}"
            if bug_data.resolution_tier_3:
                resolution_text += f" | Tier 3:{bug_data.resolution_tier_3}"
            embedding_configs.append(("resolution",resolution_text))

        #add combined embeddings
        combined_text = f"Product:{bug_data.product} | Description:{bug_data.description}"
        if bug_data.closing_notes:
            combined_text += f"| Resolution:{bug_data.closing_notes}"
        embedding_configs.append(('combined',combined_text)) #product|description|resolution

        #Generate and store embeddings

        for content_type,text in embedding_configs:
            embedding = self.generate_embedding(text)
            if not embedding or len(embedding) == 0:
                logging.error(f"Failed to generate embedding for {content_type}")
                continue

            cursor.execute("""
            insert into bug_embeddings(bug_id,content_type,content_text,embedding)
            values(%s,%s,%s,%s::vector)
            """,(bug_id,content_type,text,embedding))



    def search_similar_bugs(self, query: str, limit: int = 5, content_type: str = None, product_filter: str = None, similarity_threshold: float = 0.8) -> List[Dict]:
        """Search for similar bugs using vector similarity"""
        try:
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)
            query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
            
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM search_similar_bugs(%s::vector, %s, %s, %s, %s)
                    """, (query_embedding_str, content_type, product_filter, similarity_threshold, limit))
                    
                    # Get column names from cursor description
                    columns = [desc[0] for desc in cursor.description]
                    logging.info(f"Columns: {columns}")

                    # Convert rows to dictionaries using column names and values
                    results = []
                    for row in cursor.fetchall():
                        row_dict = dict(zip(columns, row))
                        results.append(row_dict)
                    
                    return results

        except Exception as e:
            logging.error(f"Error in search_similar_bugs: {e}")
            return []

    # def search_similar_bugs(
    #     self,
    #     query: str,
    #     content_type: Optional[str] = None,
    #     product_filter: Optional[str] = None,
    #     similarity_threshold: float = 0.3,
    #     limit: int = 10
    # ) -> List[Dict]:
    #     """Search for similar bugs using semantic similarity"""
    #     query_embedding = self.generate_embedding(query)
        
    #     with self.get_db_connection() as conn:
    #         with conn.cursor(cursor_factory=RealDictCursor) as cursor:
    #             cursor.execute("""
    #                 SELECT * FROM search_similar_bugs(%s::vector, %s, %s, %s, %s)
    #             """, (query_embedding, content_type, product_filter, similarity_threshold, limit))

    #             logging.info(f"Results: {cursor.fetchall()}")
    #             return [dict(row) for row in cursor.fetchall()]

    # """
    # Suppose the bugs table has columns id, incident_number, and description, and a row exists with (1, "INC123", "Crash on login").
    # If incident_number=INC123 is passed:

    # The query select * from bugs where incident_number = INC123 retrieves the row (1, INC123, Crash on login).
    # columns becomes ["id", "incident_number", "description"].
    # The method returns: {"id": 1, "incident_number": "INC123", "description": "Crash on login"}.

    # get_bug_by_incident_number, retrieves a bug record from a database based on a provided incident_number and returns it as a dictionary.
    # """

    def get_bug_by_incident_number(self, incident_number: str) -> Dict:
        logging.info(f"Retrieving bug by incident number: {incident_number}")
        # retrieve bug by incident number
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    select * from bugs where incident_number = %s
                """, (incident_number,))
                row = cursor.fetchone()
                logging.info(f"Retrieved bug by incident number: {incident_number}")
                logging.info(f"Retrieved bug: {row}")
                
                if row:
                    # Get column names from cursor description
                    columns = [desc[0] for desc in cursor.description]
                    # Convert row tuple to dictionary
                    return dict(zip(columns, row))
                else:
                    return None

    def get_bug_count(self):

        # Get the count of bugs in the database.
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select count(*) from bugs")
                return cursor.fetchone()[0]

    def get_embedding_count(self):
        #get the count of embeddings in the database
       with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select count(*) from bug_embeddings")
                return cursor.fetchone()[0]
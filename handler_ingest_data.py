from config import read_env_file
import pandas as pd
import logging
from bug_rag_system import BugRagSystem,BugData


'''
read csv file
create embedding
store embedding in database
'''

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    level=logging.INFO
)

def ingest_data():
    env_vars = read_env_file()

    #initialize RAG system
    rag_system = BugRagSystem({"host":env_vars.get("DB_HOST"),
        "database":env_vars.get("DB_NAME"),
        "user":env_vars.get("DB_USERNAME"),
        "password":env_vars.get("DB_PASSWORD"),
        "port":env_vars.get("DB_PORT")
    })

    #read data from csv file
    df = pd.read_csv("data.csv")
        
    return ingest_data_from_dataframe(df)

# //parse csv file    
def ingest_data_from_dataframe(df):
    logging.info("Ingesting data from dataframe")
    '''
    Ingest data from pandas Dataframe into RAG system. skips records where incident number already exists.
    Returns :
        dict: summary of Ingestion results
    '''
    env_vars = read_env_file()
    #initalize RAG system

    rag_system = BugRagSystem({

        "host":env_vars.get("DB_HOST"),
        "database":env_vars.get("DB_NAME"),
        "user":env_vars.get("DB_USERNAME"),
        "password":env_vars.get("DB_PASSWORD"),
        "port":env_vars.get("DB_PORT")
    },
        llm_api_url=env_vars.get("LLM_API_URL"),
        embedding_model=env_vars.get("EMBEDDING_MODEL_NAME")
    )

    processed_count = 0
    skipped_count = 0
    total_count = len(df)

    for index,row in df.iterrows():
        logging.info(f"Processing row {index} of {total_count}")

        incident_number = str(row["issue_key"]) if pd.notna(row['issue_key']) else None

        if not incident_number:
            logging.warning(f"Missing incident_number in row {index}")
            skipped_count += 1
            continue

    #check if incident number is already exists

        existing_bug = rag_system.get_bug_by_incident_number(incident_number)
        if existing_bug:
            logging.warning(f"Duplicate incident number {incident_number} in row {index}")
            skipped_count += 1
            continue

        try:
            #create Embedding
            logging.info(f"Creating embedding for incident number {incident_number} in row {index}")
            bug = BugData(
                incident_number = incident_number,
                product = str(row["u_product_name_display_value"]) if pd.notna(row['u_product_name_display_value']) else "",
                description = str(row["description"]) if pd.notna(row['description']) else "",
                closing_notes = str(row["close_notes"]) if pd.notna(row['close_notes']) else None,
                resolution_tier_1 = str(row["u_resolution_tier_1"]) if pd.notna(row['u_resolution_tier_1']) else None,
                resolution_tier_2 = str(row["u_resolution_tier_2"]) if pd.notna(row['u_resolution_tier_2']) else None,
                resolution_tier_3 = str(row["u_resolution_tier3"]) if pd.notna(row['u_resolution_tier3']) else None,
                problem_id = "",
                # sys_created_on=created_date,
                sys_created_on = pd.to_datetime(row["sys_created_on"], format='%m/%d/%Y').date() if pd.notna(row['sys_created_on']) else None,
                sys_created_by = str(row["sys_created_by"]).strip() if pd.notna(row['sys_created_by']) else None,
                priority = int(row["priority"]) if pd.notna(row['priority']) else None
            )

            bug_id = rag_system.store_bug(bug)#........2
            logging.info(f"Stored incident number {incident_number} in row {index} stored with ID:{bug_id}")
            processed_count += 1

        except Exception as e:
            logging.error(f"Row {index}:Error processing incident {incident_number}:{str(e)}")
            skipped_count += 1

    logging.info(f"Processed {processed_count} rows out of {total_count}")
    logging.info(f"Skipped {skipped_count} rows out of {total_count}")
    return {
        "processed_count":processed_count,
        "skipped_count":skipped_count,
        "total_count":total_count
    }
    

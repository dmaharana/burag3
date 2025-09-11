from dataclasses import dataclass
from config import read_env_file
from bug_rag_system import BugRagSystem, BugData
import pandas as pd
import logging

@dataclass
class BugSearchParams:
    query: str
    limit: int = 5
    content_type:str = None
    product_filter: str = None
    similarity_threshold: float = 0.5

@dataclass
class BugSearchResults:
    bugs: list
    report: str

def generate_bug_report(bugs:list)->str:
    report = ""
    processed_incident = {}
    logging.info(f"found {len(bugs)} similar bugs")

    for bug in bugs:
        if bug["incident_number"] in processed_incident:
            logging.info(f"skipping incident number: {bug['incident_number']}")
            continue
        processed_incident[bug["incident_number"]] = True
        report += f"Incident Number: {bug['incident_number']}:{bug['description'][:100]}... (similarity:{bug['similarity_score']*100:.3f})\n"
    return report

def search_bugs(query:str, limit:int = 5, content_type:str= None,product_filter:str = None,similarity_threshold:float=0.7) -> BugSearchResults:
    env_vars = read_env_file()
    #initalize RAG system

    rag_system = BugRagSystem({

            "host":env_vars.get("DB_HOST"),
            "database":env_vars.get("DB_NAME"),
            "user":env_vars.get("DB_USERNAME"),
            "password":env_vars.get("DB_PASSWORD"),
            "port":env_vars.get("DB_PORT")
    },

    llm_api_url = env_vars.get("LLM_API_URL"),
    embedding_model = env_vars.get("EMBEDDING_MODEL_NAME")
    )

    #search for similar bugs
    results = rag_system.search_similar_bugs(
        query=query,
        content_type=content_type,
        product_filter=product_filter,
        similarity_threshold=similarity_threshold,
        limit=limit
    )
    report = generate_bug_report(results)
    logging.info(f"found {len(results)} similar bugs")
    return BugSearchResults(bugs=results, report=report)

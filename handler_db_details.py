from flask import jsonify
from bug_rag_system import BugRagSystem
from config import read_env_file
import logging


def get_database_counts():
    #get counts of various databse entities

    try:
        env_vars = read_env_file()
        #initalize RAG system

        bug_rag_system = BugRagSystem({
            "host":env_vars.get("DB_HOST"),
            "database":env_vars.get("DB_NAME"),
            "user":env_vars.get("DB_USERNAME"),
            "password":env_vars.get("DB_PASSWORD"),
            "port":env_vars.get("DB_PORT")
        },
        llm_api_url=env_vars.get("LLM_API_URL"),
        embedding_model = env_vars.get("EMBEDDING_MODEL")
        )
        #get bug counts from Database
        bug_count = bug_rag_system.get_bug_count()
        bug_embedding_count = bug_rag_system.get_bug_embedding_count()
        

        return jsonify({
            'error':False,
            'data': {
                'bug_count':bug_count,
                'bug_embedding_count':bug_embedding_count
            }
            }), 200

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({
            'error':True,
            'message': 'Error processing request'}), 500
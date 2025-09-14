import logging
from bug_rag_system import BugRagSystem
from config import read_env_file
from result_data import Result

def get_incidents_by_days_tool(days: int) -> Result:
    
    env_vars = read_env_file()
    rag_system = BugRagSystem({
        "host": env_vars.get("DB_HOST"),
        "database": env_vars.get("DB_NAME"),
        "user": env_vars.get("DB_USERNAME"),
        "password": env_vars.get("DB_PASSWORD"),
        "port": env_vars.get("DB_PORT")
    })

    try:
        incidents = rag_system.get_incidents_by_days(days)
        logging.info(f"raw Incidents responses: {incidents}")
        if not incidents or not incidents.count > 0:
            logging.warning("No incidents found for the given days")
            return Result(error=True, message="No incidents found for the given days", result=None)
        
        return Result(error=False, message="Incidents retrieved for last days", result=incidents)
        
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return Result(error=True, message=f"Error processing request: {str(e)}", result=None)
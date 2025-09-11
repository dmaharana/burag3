import logging
from bug_rag_system import BugRagSystem
from config import read_env_file


def get_incidents_by_days_handler(days: int):
    
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
        if not incidents or not incidents.get('incidents'):
            logging.warning("No incidents found for the given days")
            return {
                "count": 0,
                "incidents": [],
                "users": [],
                "solutions": [],
                "priority": [],
                "created_on": []
            }
        count = incidents.get("count", 0)
        users = list(set([i["sys_created_by"] for i in incidents.get('incidents',[]) if i.get("sys_created_by")]))        
              
        solutions = []
        for i in incidents.get('incidents', []):
            solution_info = {
                "incident_number": i.get("incident_number"),
                "description": i.get("description"),
                "closing_notes": i.get("closing_notes"),
                "resolution_tier_1": i.get("resolution_tier_1"),
                "resolution_tier_2": i.get("resolution_tier_2"),
                "resolution_tier_3": i.get("resolution_tier_3"),
                "product": i.get("product"),
                "priority_level": i.get("priority_level"),
                "created_by": i.get("sys_created_by"),
                "created_on": str(i.get("sys_created_on")) if i.get("sys_created_on") else None
            }
            solutions.append(solution_info)
        logging.info(f"processed Incidents responses getting here")

        return {
            "count": count,
            "priority": incidents.get('priority', []),
            "incidents": incidents.get('incidents', []),
            "users": users,  # Changed from 'created_by_users' to 'users'
            "solutions": solutions,
            "created_on": incidents.get('created_date', [])
        }
        
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return {
            "count": 0,
            "incidents": [],
            "priority": [],
            "users": [],
            "solutions": [],
            "created_on": []
        }
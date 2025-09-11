# handler_tool_manager.py
from config import read_env_file
from handler_find_days import get_incidents_by_days_handler
from toolManager import OllamaToolCaller, ToolManager
import logging
import json

def tool_handler(user_message: str = "Get incidents created from last 7 days"):
    try:
        tool_caller = OllamaToolCaller("qwen3:0.6b")
    except Exception as e:
        print(f"Error initializing: {e}")
        return {'error': True, 'message': f"Error initializing: {e}"}
    try:
        response = tool_caller.chat_with_tools(user_message)
        logging.info(f"Tool response: {response}")
        result = json.loads(response)
        logging.info(f"Result check here: {result}")
        # if result contains expected keys return as is
        if all(k in result for k in ['count','users','priority','solutions','incidents','created_on']):
            return result
        return{
            "count":result.get("count",0),
            "users":result.get("users",[]),
            "priority":result.get("priority",[]),
            "solutions":result.get("solutions",[]),
            "incidents":result.get("incidents",[]),
            "created_on":result.get("created_on",[])
        }

    except Exception as e:
        logging.error(f"Error calling tool: {e}")
        return {'error': True, 'message': f"Error calling tool: {e}"}
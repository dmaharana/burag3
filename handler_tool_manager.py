# handler_tool_manager.py
from config import read_env_file
from toolManager import OllamaToolCaller, ToolManager, Result
import logging

def tool_handler(user_message: str = "Get incidents created from last 7 days") -> Result:
    try:
        tool_caller = OllamaToolCaller("qwen3:0.6b")
        responses = tool_caller.chat_with_tools(user_message)
        logging.info(f"Tool responses: {responses}")

        if not responses:
            return Result(error=True, message="No tool responses", result=None)

        logging.info(f"Responses: {responses}")
        result = None
        for tool_name, tool_response in responses.items():
            logging.info(f"Tool name: {tool_name}")
            logging.info(f"Tool response: {tool_response}")
            result = tool_response
            
        return result

    except Exception as e:
        logging.error(f"Error initializing: {e}")
        return Result(error=True, message=f"Error initializing: {e}", result=None)

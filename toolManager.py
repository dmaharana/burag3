# import json
# import requests
# from datetime import datetime
# from typing import Dict, Any, List
# import math
# import ollama
# import logging
# import psycopg2
# from handler_find_days import get_incidents_by_days

# from config import read_env_file
# from bug_rag_system import BugRagSystem

# class ToolManager:
#     """Manages tool definitions and execution for Ollama"""
    
#     def __init__(self):
#         self.tools = {}
#         self._register_tools()


#     def _register_tools(self):
#         """Register all available tools"""
#         # Calculator tool
#         self.tools['number_of_incidents'] = {
#             'type': 'function',
#             'function': {
#                 'name': 'number_of_incidents_created_in_days',
#                 'description': 'Get list of incidents or documents created in last X number of days',
#                 'parameters': {
#                     'type': 'object',
#                     'properties': {
#                         'days': {
#                             'type': 'number',
#                             'description': 'Number of days'
#                         }
#                     },
#                     'required': ['days']
#                 }
#             }
#         }

#     def get_tool_definitions(self) -> List[Dict[str, Any]]:
#         """Get all tool definitions for Ollama"""
#         return list(self.tools.values())

#     def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
#         """Execute a tool with given arguments"""
#         try:
#             if tool_name == 'number_of_incidents_created_in_days':
#                 days = arguments.get('days', 7)
#                 # days_raw = arguments.get('days', 7)
#                 # days = convert_to_days(days_raw)
#                 result = get_incidents_by_days(days)
#                 return json.dumps(result, default=str)
#             else:
#                 return json.dumps({'error':True, 'message':f"unknown tool: {tool_name}"})
#         except Exception as e:
#             return f"Error executing {tool_name}: {str(e)}"

#     # def _get_incidents_data(self, days: int) -> str:
#     #     """Get incidents data from database"""
#     #     try:
#     #         env_vars = read_env_file()
#     #         logging.info("Environment variables: {env_vars}")

#     #         #initialize RAG system
#     #         rag_system = BugRagSystem
#     #         (
#     #         {
#     #             "host":env_vars.get("DB_HOST"),
#     #             "database":env_vars.get("DB_NAME"),
#     #             "user":env_vars.get("DB_USERNAME"),
#     #             "password":env_vars.get("DB_PASSWORD"),
#     #             "port":env_vars.get("DB_PORT")
#     #         })

#     #         logging.info(f"Getting incidents created in last {days} days")
#     #         records = rag_system.get_incidents_created_last_week(days)
        
#     #         return json.dumps(records)
#     #     except Exception as e:
#     #         return f"Error getting incidents data: {str(e)}"


# class OllamaToolCaller:
#     """Main class for Ollama tool calling"""
    
#     def __init__(self, model_name: str = "qwen3:0.6b"):
#         self.tool_manager = ToolManager()
#         self.client = ollama.Client()
#         self.model_name = model_name

            
#         # Check if model is available
#         try:
#             self.client.show(self.model_name)
#         except:
#             print(f"Model {model_name} not found. Available models:")
#             models = self.client.list()
#             for model in models['models']:
#                 print(f"  - {model['name']}")
#             raise Exception(f"Please pull the model first: ollama pull {model_name}")


#     def chat_with_tools(self, user_message: str):
#         """Chat with the model using tools"""

#         system_prompt = {
#             'role': 'system',
#             'content': """You are a helpful assistant. When the user asks for data like incidents or issues created in a time period, ALWAYS use the available tools to fetch accurate data. Do not guess or simulate results. Respond with tool calls in the exact format expected. If no tool is needed, answer directly."""
#         }
#         messages = [
#             system_prompt,
#             {
#                 'role': 'user',
#                 'content': user_message
#             }
#         ]
        
#         # Get initial response from model with tools available
#         response = self.client.chat(
#             model=self.model_name,
#             messages=messages,
#             tools=self.tool_manager.get_tool_definitions()
#         )
        
#         # Check if model wants to use a tool
#         if 'tool_calls' in response['message']:
#             messages.append(response['message'])
            
#             # Execute each tool call
#             for tool_call in response['message']['tool_calls']:
#                 function_name = tool_call['function']['name']
#                 function_args = tool_call['function']['arguments']                
#                 if isinstance(function_args, str):
#                     function_args = json.loads(function_args)
#                 elif isinstance(function_args, dict):
#                         # Already a dict, use as is
#                     pass
#                 else:
#                     raise TypeError(f"Unexpected arguments type: {type(function_args)}")
                    
#                     print(f"🔧 Calling tool: {function_name}")
#                     print(f"   Arguments: {function_args}")
                
#                 # Execute the tool
#                 result = self.tool_manager.execute_tool(function_name, function_args)
                
#                 # Add tool result to messages
#                 messages.append({
#                     'role': 'tool',
#                     'content': result,
#                     'name': function_name
#                 })
            
#             # Get final response with tool results
#             final_response = self.client.chat(
#                 model=self.model_name,
#                 messages=messages
#             )
            
#             return final_response['message']['content']
#         else:
#             return response['message']['content']


# handler_tool_manager.py - Alternative approach
from config import read_env_file
# from toolManager import OllamaToolCaller, ToolManager
from handler_find_days import get_incidents_by_days_handler
import logging
import json
import ollama
from typing import Dict, Any, List

def convert_to_days(days_param):
    # Convert time period to days
    if isinstance(days_param, int):
        return days_param
    if isinstance(days_param, str):
        s = days_param.lower().strip()
        if 'week' in s:
            num = [int(x) for x in s.split() if x.isdigit()]
            return num[0] * 7 if num else 7
        elif 'month' in s:
            num = [int(x) for x in s.split() if x.isdigit()]
            return num[0] * 30 if num else 30
        elif 'year' in s:
            num = [int(x) for x in s.split() if x.isdigit()]
            return num[0] * 365 if num else 365
        elif 'day' in s:
            num = [int(x) for x in s.split() if x.isdigit()]
            return num[0] if num else 1
        else:
            try:
                return int(s)
            except ValueError:
                return 7
    return 7


class ToolManager:
    """Manages tool definitions and execution for Ollama"""
    
    def __init__(self):
        self.tools = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tools"""
        # Calculator tool
        self.tools['number_of_incidents'] = {
            'type': 'function',
            'function': {
                'name': 'number_of_incidents_created_in_days',
                'description': 'Get list of incidents or documents created in last X number of days',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'days': {
                            'type': 'number',
                            'description': 'Number of days'
                        }
                    },
                    'required': ['days']
                }
            }
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for Ollama"""
        return list(self.tools.values())

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool with given arguments"""
        logging.info(f"Executing tool: {tool_name}")
        try:
            if tool_name == 'number_of_incidents_created_in_days':
                logging.info("Executing tool: number_of_incidents_created_in_days") 

                days_raw = arguments.get('days', 7)
                days = convert_to_days(days_raw)
                logging.info(f"Days: {days}")
                result = get_incidents_by_days_handler(days)
                logging.info(f"Result: {result}")
                return json.dumps(result, default=str)
            else:
                return json.dumps({'error':True, 'message':f"unknown tool: {tool_name}"})
        except Exception as e:
            logging.error(f"Error executing {tool_name}: {str(e)}")
            return json.dumps({'error':True, 'message':f"Error executing {tool_name}: {str(e)}"})

class OllamaToolCaller:
    """Main class for Ollama tool calling"""
    
    def __init__(self, model_name: str = "qwen3:0.6b"):
        self.tool_manager = ToolManager()
        self.client = ollama.Client()
        self.model_name = model_name

            
        # Check if model is available
        try:
            self.client.show(self.model_name)
        except:
            print(f"Model {model_name} not found. Available models:")
            models = self.client.list()
            for model in models['models']:
                print(f"  - {model['name']}")
            raise Exception(f"Please pull the model first: ollama pull {model_name}")


    def chat_with_tools(self, user_message: str):
        """Chat with the model using tools"""

        system_prompt = {
            'role': 'system',
            'content': """You are a helpful assistant. When the user asks for data like incidents or issues created in a time period, ALWAYS use the available tools to fetch accurate data. Do not guess or simulate results. Respond with tool calls in the exact format expected. If no tool is needed, answer directly."""
        }
        messages = [
            system_prompt,
            {
                'role': 'user',
                'content': user_message
            }
        ]
        
        # Get initial response from model with tools available
        response = self.client.chat(
            model=self.model_name,
            messages=messages,
            tools=self.tool_manager.get_tool_definitions()
        )
        
        # Check if model wants to use a tool
        if 'tool_calls' in response['message']:
            messages.append(response['message'])
            
            # Execute each tool call
            for tool_call in response['message']['tool_calls']:
                function_name = tool_call['function']['name']
                function_args = tool_call['function']['arguments']                
                if isinstance(function_args, str):
                    function_args = json.loads(function_args)
                elif isinstance(function_args, dict):
                        # Already a dict, use as is
                    pass
                else:
                    raise TypeError(f"Unexpected arguments type: {type(function_args)}")
                    
                    print(f"🔧 Calling tool: {function_name}")
                    print(f"   Arguments: {function_args}")
                
                # Execute the tool
                result = self.tool_manager.execute_tool(function_name, function_args)
                logging.info(f"Tool result: {result}")

                # Add tool result to messages
                messages.append({
                    'role': 'tool',
                    'content': result,
                    'name': function_name
                })
            
            # Get final response with tool results
            final_response = self.client.chat(
                model=self.model_name,
                messages=messages
            )
            
            return final_response['message']['content']
        else:
            return response['message']['content']



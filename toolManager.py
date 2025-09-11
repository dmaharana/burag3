# handler_tool_manager.py - Alternative approach
from tool_find_days import get_incidents_by_days_tool
import logging
import json
import ollama
from typing import Dict, Any, List
from result_data import Result

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

    def convert_to_days(self,days_param) -> int:
        """Convert time period to days"""
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


    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Result:
        """Execute a tool with given arguments"""
        logging.info(f"Executing tool: {tool_name}")
        try:
            if tool_name == 'number_of_incidents_created_in_days':
                logging.info("Executing tool: number_of_incidents_created_in_days") 

                days_raw = arguments.get('days', 7)
                days = self.convert_to_days(days_raw)
                logging.info(f"Days: {days}")
                result = get_incidents_by_days_tool(days)
                logging.info(f"Result: {result}")

                return result
            else:
                return Result(error=True, message=f"unknown tool: {tool_name}", result=None)
        except Exception as e:
            logging.error(f"Error executing {tool_name}: {str(e)}")
            return Result(error=True, message=f"Error executing {tool_name}: {str(e)}", result=None)

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


    def chat_with_tools(self, user_message: str) -> Dict[str, Result]:
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
        

        logging.info(f"Initial response: {response}")
        # Get tool calls from response
        tool_responses = {} # tool_name: response

        # Check if model wants to use a tool
        if 'tool_calls' in response['message']:
            logging.info("Model wants to use a tool")
            # Execute each tool call
            for tool_call in response['message']['tool_calls']:
                function_name = tool_call['function']['name']
                function_args = tool_call['function']['arguments']     
                
                logging.info(f"Function name: {function_name}")
                logging.info(f"Function arguments: {function_args}")

                if isinstance(function_args, str):
                    function_args = json.loads(function_args)
                elif isinstance(function_args, dict):
                        # Already a dict, use as is
                    pass
                else:
                    logging.error(f"Unexpected arguments type: {type(function_args)}")
                    raise TypeError(f"Unexpected arguments type: {type(function_args)}")
                
                # Execute the tool
                result = self.tool_manager.execute_tool(function_name, function_args)
                logging.info(f"Tool result: {result}")
                tool_responses[function_name] = result
            
        return tool_responses



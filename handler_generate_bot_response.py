import logging
from config import read_env_file
from constants import STREAM_RESPONSE
from openai import OpenAI, api_key
from handler_search import search_bugs                                                                                                                                                                                                         

def create_request_messages_from_payload(user_messages):
    #create request messages from payload
    messages=[]
    logging.info(f'creating request messages from payload : {user_messages}')
    for item in user_messages:
        for msg in item.get('conversation',[]):
            messages.append({"role":msg['role'],"content":msg['content']})
    return messages

def add_response_to_history(messages, bot_response):
    #add bot response and user response to history
    user_messages =messages[-1]['conversation'][0]['content'] if messages else ""
    logging.info(f"user message: {user_messages}")
    logging.info(f"Bot:{bot_response}")

    response_message = {
        "id":messages[-1]['id'],
        "conversation":[
            {"role":"user","content":user_messages},
            {"role":"assistant","content":bot_response}
        ]
    }
    return response_message


def generate_bot_response_openai(messages, env_var):
    "Generate a response from the OpenAI API"

    client=OpenAI(
        base_url=f"{env_vars["LLM_API_URL"]}/v1",
        api_key="ollama"
    )
    response = client.chat.completions.create(
        model=env_vars["CHAT_MODEL_NAME"],
        messages=messages,
        stream = STREAM_RESPONSE
    )
    if response.choices:
        return response.choices[0].message.content

def generate_closing_notes(similar_bugs_details:list) -> str:

    #generate closing notes based on similar bugs
    closing_notes = ""
    processed_incident = {}
    if similar_bugs_details:
        for bug in similar_bugs_details:
            if bug['incident_number'] in processed_incident:
                continue
            processed_incident[bug['incident_number']] = True
            closing_notes = f"Incident Number: {bug['incident_number']}:{bug['description'][:100]}... (similarity:{bug['similarity_score']*100:.3f})\n"
    return closing_notes


def send_bot_response(payload):
    """ Generate a bot response based on the user message and conversation history"""
    request_received_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Rquest received at:{request_received_time}")
    
    env_vars=read_env_file()
    request_message = create_request_messages_from_payload(payload['messages'])
    
    query = request_messages[-1]['content'] if request_messages else ""
    logging.info(f"search query: {query}") 
    
    #search for similar bugs
    result = search_bugs(query=query)
    logging.info(f"found similar bugs: {result.bugs}") 
    
    if result.bugs:
        closing_notes = genearate_closing_notes(result.bugs)
        logging.info(f"closing notes generated:{closing_notes}")
        system.prompt = f"you are a helpful assistant. Use the following context that were resolutions provided for similar incidents, to answer the user query: {query} \n CONTEXT: {closing_notes}"
    else:
        system_prompt = f"you are a helpful assistant. Answer concisely the user query: {query}"
        similar_bugs = "No similar bugs found"
        
    #add system prompt to request messages
    request_messages.insert(0,{"role":"system","content":system_prompt})
    
    bot_response = generate_bot_response_openai(request_messages, env_vars)
    
    #add similar bugs to bot_response
    bot_response = f"{bot_response}\n\nSimilar incidents:\n {result.report}"
    
    #add user message and bot response to converdation history
    message = add_response_to_history(payload['messages'], bot_response)   
    return message                                                                                                                                                      
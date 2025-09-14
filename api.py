from flask import Flask,request,jsonify
from flask_cors import CORS
from flask import Flask
import os
import logging
import chardet
import pandas as pd
from werkzeug.utils import secure_filename
from handler_ingest_data import ingest_data_from_dataframe
from handler_search import search_bugs
from config import read_env_file
from handler_tool_manager import tool_handler
from tool_manager import Result


app = Flask(__name__)
CORS(app) #enables CORS for react frontend

# Configuration
BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploadsv01')
# ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_EXTENSIONS = {'csv'}

# Ensure directories exists
os.makedirs(BUILD_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"Serving static files from: {BUILD_DIR}")

#Configure logging to include line number, filename and log level
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    level=logging.INFO
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_file_encoding(file_path):
    try:
        with open(file_path,'rb') as f:
            logging.info(f"Trying to detect file encoding")
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding=result['encoding']
            confidence = result['confidence']
            logging.info(f"File encoding detected as {encoding} with confidence {confidence}")
            return encoding
    except Exception as e:
        logging.error(f"Error detecting file encoding: {e}")
        return 'utf-8'

def read_csv_with_encoding_detection(file_path):
    encoding_to_try = [
        'utf-8',
        'utf-8-sig',
        'windows-1252',
        'iso-8859-1',
        'cp1252',
        'ascii'

    ]

    detected_encoding = detect_file_encoding(file_path)
    if detected_encoding:
        encoding_to_try.insert(0, detected_encoding)

    #remove duplicates while preserving order
    encoding_to_try = list(dict.fromkeys(encoding_to_try))

    for encoding in encoding_to_try:
        try:
            logging.info(f"Trying to read file with encoding {encoding}")
            df = pd.read_csv(file_path, encoding=encoding)
            print(df.columns)
            logging.info(f"Successfully read file with encoding {encoding}")
            return df
        except Exception as e:
            logging.error(f"Error reading file with encoding {encoding}: {str(e)}")

            continue
    raise ValueError(f"Could not read file with any of the following encodings: {', '.join(encoding_to_try)}")
    

@app.route('/')
def index():
    return 'hello world'


@app.route('/api/ingest',methods=['POST'])
def ingest_bug_data():
    #ingest data into system from uploaded csv file
    try:
        if 'file' not in request.files:
            return jsonify({
                'error':True,
                'message': 'No file uploaded'
                }), 400
        logging.info("File uploaded successfully")
        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'error':True,
                'message': 'No file selected'
                }), 400
        logging.info("File selected successfully")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            logging.info(f"Saving file to {file_path}")
            file.save(file_path)
            logging.info("File saved successfully")
            #read csv file into dataframe with encoding detection
            df = read_csv_with_encoding_detection(file_path)
            logging.info("File read successfully")
            result= ingest_data_from_dataframe(df)
            logging.info("Data ingested successfully")
            #clean up the uploaded file
            os.remove(file_path)

            return jsonify({
                'error':False,
                'message':'Data ingested successfully',
                'processed_records': result['processed_count'],
                'skipped_records':result['skipped_count'],
                'total_records':result['total_count']
            }),200
            
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({
            'error':True,
            'message': 'Error processing request'}), 500

#search DB for specific query 
@app.route('/api/search', methods=['POST'])
def search_database():
    #search the database for specific queries
    logging.info("Search request received")
    query = request.json.get('query','')
    logging.info(f"Search query: {query}")
    print(f"query: {query}")
    limit = request.json.get('limit',5)
    logging.info(f"Search query: {query}")
    content_type = request.json.get('content_type',None)
    product_filter = request.json.get('product_filter',None)
    similarity_threshold = request.json.get('similarity_threshold',0.5)

    results = search_bugs(
        query=query,
        limit=limit,
        content_type=content_type,
        product_filter=product_filter,
        similarity_threshold=similarity_threshold
    )

    return jsonify({
        'error':False,
        'message': 'Request processed successfully',
        'results': results
        }), 200

#get count of various database entities.

# @app.route('/api/db/stats', methods=['GET'])
# def get_db_count():

#     try:
#         return get_database_count()
#     except Exception as e:
#         logging.error(f"Error processing request: {dtr(e)}")
#         return jsonify({
#             'error':True,
#             'message': 'Error processing request'}), 500

@app.route('/api/chat', methods=['DELETE'])
def stop_response_generation():
    #stop the response generation
    try:
        return jsonify({
            'error':False,
            'message': 'Response generation stopped successfully'
            }), 200

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({
            'error':True,
            'message': 'Error processing request'}), 500

# @app.route('/api/incident_days', methods=['POST'])
# def incidents_last_week():
#     try:
#         result = get_incidents_last_week_handler()
#         logging.info(f"Retrieved {len(result['incidents'])} incidents from last week")       
#         return jsonify({
#             'error':False,
#             'message': 'Incidents from last week retrieved successfully',
#             'count': result['count'],
#             'incident_numbers': result['incident_numbers'],
#             'created_by_users': result['created_by_users'],
#             'incidents': result['incidents']
#             }), 200

#     except Exception as e:
#         logging.error(f"Error processing request: {e}")
#         return jsonify({
#             'error':True,
#             'message': 'Error processing request'}), 500


@app.route('/api/toolcall_days', methods=['POST'])
def get_days_toolcall():
    logging.info("Toolcall request received")
    try:
        data = request.get_json()
        user_message = data['message'] if 'message' in data else None
        logging.info(f"User message: {user_message}")

        result = tool_handler(user_message)
        if result.error:
            return jsonify(result), 500

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        result = Result(error=True, message=f"Error processing request: {str(e)}", result=None)
        return jsonify(result), 500


# Alternative endpoint with configurable days parameter

if __name__ == '__main__':
    if not os.path.exists(BUILD_DIR):
        print(f"warning:React build directory {BUILD_DIR} does not exist")

    env_cfg = read_env_file()
    app_port = env_cfg.get("APP_PORT",5000)
    app.run(host='0.0.0.0', port=app_port, debug=True)

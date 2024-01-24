# Import necessary libraries
from flask import Flask, request, jsonify
from pandasai import SmartDataframe
from pandasai.llm import OpenAI
from sqlalchemy import text
from waitress import serve
import pandas as pd
import matplotlib
import base64
import io

# Initialize Flask application
app = Flask(__name__)
df = None
matplotlib.use('Agg')

# Load configuration from .config file
app.config.from_pyfile('.config')

# Access the configuration values
API_KEY = app.config['OPENAI_API_KEY']
SERVERNAME = app.config['SERVERNAME']
DATABASE = app.config['DATABASE']

# Function to convert base64 image to bytes
def get_image(base64_string):
   """
   Convert a base64 string into bytes.

   Parameters:
   base64_string (str): The base64 string to be converted.

   Returns:
   BytesIO object: The bytes representation of the base64 string.
   """
   base64_bytes = base64_string.encode('utf-8')
   decoded_bytes = base64.b64decode(base64_bytes)
   return io.BytesIO(decoded_bytes)

@app.route('/datatable', methods=['GET'])
def db_connection():
   """
   Connect to the database and fetch data based on the provided year and company name.

   Parameters:
   year (str): The year for which data needs to be fetched.
   company_name (str): The name of the company for which data needs to be fetched.

   Returns:
   JSON response: The length of the dataframe containing the fetched data.
   """
   try:
       global df
       global SERVERNAME
       global DATABASE
       # Create connection string
       uri = "mssql+pyodbc://" + SERVERNAME + "/" + DATABASE + "?driver=SQL+Server+Native+Client+11.0"
       # Get year and company name from request arguments
       year = request.args.get('year')
       company_name = request.args.get('company_name')
       # Create SQL query
       query = f"SELECT * FROM dbo.[{year}_open_payments_data] WHERE [Submitting Company] = '{company_name}'"
       # Execute SQL query and store result in dataframe
       df = pd.read_sql(text(query), con=uri)
       # Convert few lines to JSON format for view
       response = df.head(4).to_json(orient="records")
       # Initialize OpenAI model
       llm = OpenAI(api_token = API_KEY, model = "gpt-4", temperature=0.5, max_tokens=1024, top_p=1, frequency_penalty=0, presence_penalty=0)
       # Convert dataframe to SmartDataframe
       df = SmartDataframe(df, config={"llm": llm, "conversational": False})
       # Get length of dataframe
       dataframe_length = len(df)
   except Exception as e:
       print(e)
       return jsonify({'msg': str(e)}), 400
   finally:
       print("Client IP: " + request.remote_addr + " Query: " + query)
       return jsonify({'msg': response, 'msg_len': dataframe_length}), 200

@app.route('/prompt', methods=['GET'])
def process():
   """
   Process a given prompt and return the response.

   Parameters:
   prompt (str): The prompt to be processed.

   Returns:
   JSON response: The response to the given prompt.
   """
   global df
   response_type = None
   prompt = request.args.get('prompt')
   response = df.chat(prompt)
   print(response)
   if response is not None:
       if isinstance(response, SmartDataframe):
           pandas_df = pd.DataFrame(response, columns=response.columns)
           response = pandas_df.to_json(orient="records")
           response_type = "table"
       else:
           response = str(response)
           response_type = "text"
   else:
       print("Found file")
       response_type = "base64"       
       with open("D:/Gen_AI/exports/charts/temp_chart.png", "rb") as img_file:
           print("In the path")
           response = base64.b64encode(img_file.read()).decode('utf-8')
           print(response)
   return jsonify({'msg': response, 'type': response_type}), 200

@app.route('/')
def index():
   """
   Default route that returns a greeting message.

   Returns:
   str: A greeting message.
   """
   return "Hello Friend! Yes, the server is running 🏃"

if __name__ == '__main__':
   """
   Main entry point of the application.
   """
   try:
       HOST = app.config['HOST']
       PORT = app.config['PORT']
   except ValueError:
       HOST = "localhost"
       PORT = 5555
   print("Server running at ", HOST, " @ ", PORT)
   serve(app, host=HOST, port=PORT)

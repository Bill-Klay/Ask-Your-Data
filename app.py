from flask import Flask, request, jsonify
from pandasai import SmartDataframe
from pandasai.llm import OpenAI
import pandas as pd
import base64
import io
import os


app = Flask(__name__)
df = None

# Function to convert base64 image to bytes
def get_image(base64_string):
    base64_bytes = base64_string.encode('utf-8')
    decoded_bytes = base64.b64decode(base64_bytes)
    return io.BytesIO(decoded_bytes)

@app.route('/datatable', methods=['GET'])
def db_connection():
    try:
        global df
        uri = 'mssql+pyodbc://10.0.100.175/IndustryData_Chatbot?driver=SQL+Server+Native+Client+11.0'
        year = request.args.get('year')
        company_name = request.args.get('company_name')
        query = f"SELECT * FROM dbo.[{year}_open_payments_data] WHERE submitting_Company_Name = '{company_name}'"
        df = pd.read_sql(query, con=uri)
        llm = OpenAI(api_token = "")
        df = SmartDataframe(df, config={"llm": llm, "conversational": False})
    except Exception as e:
        print(e)
        return jsonify({'msg': str(e)}), 400
    finally:
        print(len(df))
        return jsonify({'msg': 'success'}), 200
    
@app.route('/prompt', methods=['GET'])
def process():
    global df
    prompt = request.args.get('prompt')
    response = df.chat(prompt)
    if response is not None:
        if isinstance(response, SmartDataframe):
            pandas_df = pd.DataFrame(response, columns=response.columns)
            response = pandas_df.to_json(orient="records")
        else:
            response = str(response)

    else:
        print(response, type(response))
        print("Image found!")        
        with open("./temp_chart.png", "rb") as img_file:
            response = base64.b64encode(img_file.read()).decode('utf-8')

    return jsonify({'msg': response}), 200

@app.route('/')
def index():
    return "Hello Friend! Yes, the server is running 🏃"

if __name__ == '__main__':
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
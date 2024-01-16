from pandasai import SmartDataframe
from pandasai.llm import OpenAI
import streamlit as st
import pandas as pd
from PIL import Image
import base64
import json
import time
import toml
import os
import io

# Define the path to your config file
config_path = './config.toml'

# Check if the config file exists
if os.path.isfile(config_path):
    # Load the config file
    config = toml.load(config_path)
    st.session_state.openai_api_key = config['DEFAULT']['OPENAI_API_KEY']
else:
    st.info("Could not find OpenAI Key or Config file")
    st.stop() 

# Access the configuration variables
DATABASE = config['DEFAULT']['DATABASE']
SERVERNAME = config['DEFAULT']['SERVERNAME']

uri = "mssql+pyodbc://" + SERVERNAME + "/" + DATABASE + "?driver=SQL+Server+Native+Client+11.0"
load_dataframe = False

# Function to convert base64 image to bytes
def get_image(base64_string):
    base64_bytes = base64_string.encode('utf-8')
    decoded_bytes = base64.b64decode(base64_bytes)
    return io.BytesIO(decoded_bytes)

with st.sidebar:
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"
    if "json_messages_chat" in st.session_state:
        json_string = json.dumps(st.session_state['json_messages_chat'])
        st.download_button("Export Chat", json_string, file_name='Chat History.json', mime='application/json')


st.title("📝 DB-QA")
st.caption("🚀 A streamlit chatbot powered by GPT-4")

col1, col2 = st.columns(2)

# Initialize the company select box with None
if "select_company" not in st.session_state:
    st.session_state.company_list = []
    st.session_state.select_company = None
    st.session_state.prev_company = None
    st.session_state.dataframe_time = None
    st.session_state.query_time = 0.000


# Initialize the year select box with None
if "select_year" not in st.session_state:
    st.session_state.select_year = None

# Initialize the dataframe with None
if "df" not in st.session_state:
    st.session_state.df = None

st.session_state.select_year = col1.selectbox('Select Year', ('2018', '2019', '2020', '2021', '2022'), index=None, placeholder='Select a year')

# Always show the company select box, but only populate it after a year is selected
if st.session_state.select_year is not None and not st.session_state.company_list:
    company_list = pd.read_sql(f"SELECT DISTINCT submitting_Company_Name FROM dbo.[{st.session_state.select_year}_open_payments_data]", con=uri)
    st.session_state.company_list = company_list['submitting_Company_Name'].tolist()

st.session_state.select_company = col2.selectbox('Select Company', st.session_state.company_list,index=None, placeholder='Select a company')
if st.session_state.select_company != st.session_state.prev_company:
    st.session_state.prev_company = st.session_state.select_company
    load_dataframe = True

# Only fetch data and show the dataframe header when both year and company have been selected

if load_dataframe:
    st.caption("Peek into the uploaded dataframe:")
    start = time.time()
    with st.spinner("Loading dataframe..."):
        query = f"SELECT * FROM dbo.[{st.session_state.select_year}_open_payments_data] WHERE submitting_Company_Name = '{st.session_state.select_company}'"
        st.session_state.df = pd.read_sql(query, con=uri)
        st.dataframe(st.session_state.df.head(3))
    end = time.time()
    st.session_state.dataframe_time = end - start
    st.caption(f"Time taken to load dataframe: {round(st.session_state.dataframe_time, 3)} seconds")
    st.caption(f"Number of rows in dataframe: {len(st.session_state.df)}")
    if "messages_chat" not in st.session_state:
        # st.chat_message("assistant").write("Ask something about your data.")
        st.session_state["messages_chat"] = []
        st.session_state["json_messages_chat"] = []
        st.session_state.messages_chat.append({"role": "assistant", "content": "Ask something about your data"})
elif not load_dataframe and st.session_state.select_year is not None and st.session_state.select_company is not None:
    st.dataframe(st.session_state.df.head(3))
    st.caption(f"Time taken to load dataframe: {round(st.session_state.dataframe_time, 3)} seconds")
    st.caption(f"Number of rows in dataframe: {len(st.session_state.df)}")

if "messages_chat" in st.session_state:
    for msg in st.session_state.messages_chat:
        if isinstance(msg['content'], str) or isinstance(msg['content'], int) or isinstance(msg['content'], float):
            st.chat_message(msg["role"]).write(str(msg['content']))
        elif isinstance(msg['content'], SmartDataframe):
            with st.chat_message(msg["role"]):
                response = pd.DataFrame(msg['content'], columns=msg['content'].columns)
                st.dataframe(response)
        elif isinstance(msg['content'], Image.Image):
            with st.chat_message(msg["role"]):
                st.image(msg['content'])

if prompt := st.chat_input(max_chars=4000):
    if "openai_api_key" not in st.session_state:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    st.session_state.messages_chat.append({"role": "user", "content": prompt})
    if "json_messages_chat" not in st.session_state:
        st.session_state["json_messages_chat"] = []
    else:
        st.session_state.json_messages_chat.append({"role": "user", "content": prompt })
    st.chat_message("user").write(prompt)
    llm = OpenAI(api_token = st.session_state.openai_api_key)
    df = SmartDataframe(st.session_state.df, config={"llm": llm, "conversational": False})
    
    query_start = time.time()
    with st.spinner('Executing user prompt...'):
        response = df.chat(prompt)
    query_end = time.time()
    st.session_state.query_time = query_end - query_start
    
    if response is not None:
        st.session_state.messages_chat.append({"role": "assistant", "content": response})
        if type(response) is SmartDataframe:
            with st.chat_message("assistant"):
                response = pd.DataFrame(response, columns=response.columns)
                st.dataframe(response)
            st.session_state.json_messages_chat.append({"role": "assistant", "content": str(response) })
        else:
            st.chat_message("assistant").write(str(response))
            st.session_state.json_messages_chat.append({"role": "assistant", "content": response })

    else:        
        with open("./temp_chart.png", "rb") as img_file:
            image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            image_bytes = get_image(image_base64) # Convert base64 string to bytes
            image = Image.open(image_bytes) # Open the image with PIL
            st.session_state.messages_chat.append({"role": "assistant", "content": image})
            st.session_state.json_messages_chat.append({"role": "assistant", "content": "[plot]" })

        with st.chat_message("assistant"):
            st.image(image)
    st.caption(f"Time taken to answer: {round(st.session_state.query_time, 3)} seconds")
    # st.chat_message("assistant").write(f"Time taken to answer: {round(query_end-query_start, 3)}")
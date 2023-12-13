from pandasai import SmartDataframe
from pandasai.llm import OpenAI
import streamlit as st
import dask.dataframe as dd
import base64
import io
from PIL import Image
import json
import io

uri = 'mssql+pyodbc://10.0.100.140/IndustryData?driver=SQL+Server+Native+Client+11.0'

# Function to convert base64 image to bytes
def get_image(base64_string):
    base64_bytes = base64_string.encode('utf-8')
    decoded_bytes = base64.b64decode(base64_bytes)
    return io.BytesIO(decoded_bytes)

with st.sidebar:
    if "openai_api_key" in st.session_state:
        st.session_state.openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password", value=st.session_state.openai_api_key)
    else:
        st.session_state.openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"
    if "json_messages" in st.session_state:
        json_string = json.dumps(st.session_state['json_messages'])
        st.download_button("Export Chat", json_string, file_name='Chat History.json', mime='application/json')

st.title("📝 DB-QA")
st.caption("🚀 A streamlit chatbot powered by GPT-4")

if "df" not in st.session_state:
    st.caption("Peek into the uploaded dataframe:")
    with st.spinner("Loading dataframe..."):
        df = dd.read_sql_table("open_payments_data", index_col='Record_ID', npartitions=10, con=uri)
        st.session_state.df = df
        st.dataframe(df.head(3))
    if "messages" not in st.session_state:
        st.chat_message("assistant").write("Ask something about your data.")
        st.session_state["messages"] = []
        st.session_state["json_messages"] = []
   

if "messages" in st.session_state:
    for msg in st.session_state.messages:
        if isinstance(msg['content'], str) or isinstance(msg['content'], int) or isinstance(msg['content'], float):
            st.chat_message(msg["role"]).write(msg['content'])
        elif isinstance(msg['content'], SmartDataframe):
            with st.chat_message(msg["role"]):
                response = dd(msg['content'], columns=msg['content'].columns)
                st.dataframe(response)
        elif isinstance(msg['content'], Image.Image):
            with st.chat_message(msg["role"]):
                st.image(msg['content'])

if prompt := st.chat_input(max_chars=4000):
    if "openai_api_key" not in st.session_state:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    if "json_messages" not in st.session_state:
        st.session_state["json_messages"] = []
    else:
        st.session_state.json_messages.append({"role": "user", "content": prompt })
    st.chat_message("user").write(prompt)
    llm = OpenAI(api_token = st.session_state.openai_api_key )
    df = SmartDataframe(st.session_state.df, config={"llm": llm, "conversational": False})
    
    with st.spinner('Executing user prompt...'):
        response = df.chat(prompt)
    
    if response is not None:
        st.session_state.messages.append({"role": "assistant", "content": response})
        if type(response) is str or type(response) is int or type(response) is float:
            st.chat_message("assistant").write(response)
            st.session_state.json_messages.append({"role": "assistant", "content": response })
        elif type(response) is SmartDataframe:
            with st.chat_message("assistant"):
                response = dd(response, columns=response.columns)
                st.dataframe(response)
            st.session_state.json_messages.append({"role": "assistant", "content": str(response) })

    else:        
        with open("./temp_chart.png", "rb") as img_file:
            image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            image_bytes = get_image(image_base64) # Convert base64 string to bytes
            image = Image.open(image_bytes) # Open the image with PIL
            st.session_state.messages.append({"role": "assistant", "content": image})
            st.session_state.json_messages.append({"role": "assistant", "content": "[plot]" })

        with st.chat_message("assistant"):
            st.image(image)
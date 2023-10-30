import io
import json
import base64
import openai
from PIL import Image
import streamlit as st
from pandasai import SmartDataframe

# Function to convert base64 image to bytes
def get_image(base64_string):
    base64_bytes = base64_string.encode('utf-8')
    decoded_bytes = base64.b64decode(base64_bytes)
    return io.BytesIO(decoded_bytes)

with st.sidebar:
    st.session_state.openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"
    if "json_chat_messages" in st.session_state:
        json_string = json.dumps(st.session_state['json_chat_messages'])
        st.download_button("Export Chat", json_string, file_name='Chat History.json', mime='application/json')

st.title("💬 Chatbot")
st.caption("🚀 A streamlit chatbot powered by OpenAI LLM")
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
    st.session_state.chat_messages.append({"role": "assistant", "content": "How can I help you?"})

if "chat_messages" in st.session_state:
    for msg in st.session_state.chat_messages:
        if isinstance(msg['content'], str) or isinstance(msg['content'], int) or isinstance(msg['content'], float):
            st.chat_message(msg["role"]).write(msg['content'])
        elif isinstance(msg['content'], SmartDataframe):
            with st.chat_message(msg["role"]):
                st.dataframe(msg['content'])
        elif isinstance(msg['content'], Image.Image):
            with st.chat_message(msg["role"]):
                st.image(msg['content'])

if prompt := st.chat_input():
    if "openai_api_key" not in st.session_state:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    if "json_chat_messages" not in st.session_state:
        st.session_state["json_chat_messages"] = []
    else:
        st.session_state.json_chat_messages.append({"role": "user", "content": prompt })
    st.chat_message("user").write(prompt)
    openai.api_key = st.session_state.openai_api_key
    
    with st.spinner('Executing user prompt...'):
        msg = openai.ChatCompletion.create(model="gpt-4", messages=st.session_state.chat_messages)
        response = msg.choices[0].message
    
    st.chat_message("assistant").write(response.content)
    st.session_state.chat_messages.append(response)
    st.session_state.json_chat_messages.append(response)
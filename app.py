import requests
import streamlit as st

# Flask API endpoint - replace with your actual endpoint
FLASK_ENDPOINT = "http://127.0.0.1:5001/search"

with st.sidebar:
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

st.title("💬 Chatbot")
st.caption("🚀 A streamlit chatbot powered by OpenAI LLM")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    # Append user's prompt to the conversation
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Prepare data for the POST request to Flask
    data = {"query": prompt}

    # Send POST request to Flask app
    response = requests.post(FLASK_ENDPOINT, json=data)

    if response.status_code == 200:
        # Get the response from Flask and display it
        results = response.json()
        msg = results['results']  # Assuming 'results' contains the text to be displayed
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant").write(msg)
    else:
        error_message = "Failed to retrieve data. Please try again."
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        st.chat_message("assistant").write(error_message)

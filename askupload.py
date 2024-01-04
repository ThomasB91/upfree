import streamlit as st
# from langchain import LangChain
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # Load the environment variables from .env file
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI()

# Initialize SentenceTransformer
model = SentenceTransformer('sentence-transformers/multi-qa-MiniLM-L6-cos-v1')

# Streamlit interface
st.title("File Vectorization and Question Answering App")

# File upload
uploaded_file = st.file_uploader("Upload a file for vectorization")
question = st.text_input("Ask a question about the file")

# Process file and answer questions
if uploaded_file is not None and question:
    # Read file content
    file_content = uploaded_file.getvalue().decode()

    # Vectorize content
    vectorized_content = model.encode([file_content])

    # New way to call the OpenAI API
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Adjust the model as needed
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ]
    )

    # Extracting and displaying the answer
    answer = response['choices'][0]['message']['content']
    st.write("Answer:", answer)

# Run this with `streamlit run your_script.py`
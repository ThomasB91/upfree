import streamlit as st
# from langchain import LangChain
from sentence_transformers import SentenceTransformer
import openai

# Initialize LangChain and SentenceTransformer
# langchain = LangChain()
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

    # Answer the question using OpenAI API (replace with RAG if needed)
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Question: {question}\nAnswer:",
        max_tokens=150
    )

    st.write("Answer:", response.choices[0].text.strip())

# Run this with `streamlit run your_script.py`
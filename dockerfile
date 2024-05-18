FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Replace the URL with your Streamlit app's repository URL
RUN git clone https://github.com/ThomasB91/upfree .

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "upfree/test_copy.py", "--server.port=8501", "--server.address=0.0.0.0"]

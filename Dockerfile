# Dockerfile — ChatDEVA Smart Container
# SERVICE_TYPE=backend → runs FastAPI
# SERVICE_TYPE=frontend → runs Streamlit

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ libsqlite3-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/chatdeva_uploads /tmp/chatdeva_vectors /app/.streamlit

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/bin/bash", "/app/start.sh"]

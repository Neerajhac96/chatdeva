# Dockerfile — ChatDEVA Smart Container
# Runs either backend OR frontend based on SERVICE_TYPE environment variable
# 
# Backend service: set SERVICE_TYPE=backend in Railway Variables
# Frontend service: set SERVICE_TYPE=frontend in Railway Variables

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install torch CPU-only (needed for backend, skipped at runtime for frontend)
RUN pip install --no-cache-dir torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu

# Install all dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Copy streamlit config
COPY .streamlit /app/.streamlit

# Create necessary directories
RUN mkdir -p /tmp/chatdeva_uploads /tmp/chatdeva_vectors

# Smart startup script — reads SERVICE_TYPE to decide what to run
RUN echo '#!/bin/bash\n\
if [ "$SERVICE_TYPE" = "frontend" ]; then\n\
    echo "Starting Streamlit frontend..."\n\
    exec streamlit run frontend/app.py \\\n\
        --server.port "${PORT:-8501}" \\\n\
        --server.address "0.0.0.0" \\\n\
        --server.headless true\n\
else\n\
    echo "Starting FastAPI backend..."\n\
    exec uvicorn backend.main:app \\\n\
        --host 0.0.0.0 \\\n\
        --port "${PORT:-8000}"\n\
fi' > /app/start.sh && chmod +x /app/start.sh

CMD ["/bin/bash", "/app/start.sh"]

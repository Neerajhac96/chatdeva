#!/bin/bash
echo "SERVICE_TYPE is: $SERVICE_TYPE"

if [ "$SERVICE_TYPE" = "frontend" ]; then
    echo "Starting Streamlit frontend on port $PORT..."
    exec streamlit run frontend/app.py \
        --server.port "${PORT:-8501}" \
        --server.address "0.0.0.0" \
        --server.headless true
else
    echo "Starting FastAPI backend on port $PORT..."
    exec uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port "${PORT:-8000}"
fi

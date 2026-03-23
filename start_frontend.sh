#!/bin/bash
# start_frontend.sh — Streamlit startup script
# Reads $PORT from Railway environment and passes it explicitly

exec streamlit run frontend/app.py \
    --server.port "${PORT:-8501}" \
    --server.address "0.0.0.0" \
    --server.headless true

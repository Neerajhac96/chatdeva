#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# run.sh — Start ChatDEVA backend + frontend together
# Usage: chmod +x run.sh && ./run.sh
# ─────────────────────────────────────────────────────────────────────

set -e

echo "🚀 Starting ChatDEVA..."

# Ensure uploads and vector_store dirs exist
mkdir -p uploads vector_store

# Start FastAPI backend in background
echo "▶ Starting FastAPI backend on http://localhost:8000 ..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend to start..."
until curl -s http://localhost:8000/health > /dev/null; do
    sleep 1
done
echo "✅ Backend ready."

# Start Streamlit frontend
echo "▶ Starting Streamlit frontend on http://localhost:8501 ..."
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "════════════════════════════════════════"
echo "  ChatDEVA is running!"
echo "  Frontend : http://localhost:8501"
echo "  API docs : http://localhost:8000/docs"
echo "  Health   : http://localhost:8000/health"
echo "════════════════════════════════════════"
echo "  Default admin: username=admin password=admin123"
echo "  ⚠️  Change the admin password immediately!"
echo "════════════════════════════════════════"
echo ""
echo "Press Ctrl+C to stop both services."

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID

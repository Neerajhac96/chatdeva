@echo off
REM ─────────────────────────────────────────────────────────────────────
REM run.bat — Start ChatDEVA on Windows
REM Usage: Double-click or run from terminal in project root
REM ─────────────────────────────────────────────────────────────────────

echo Starting ChatDEVA...

REM Create required directories
if not exist uploads mkdir uploads
if not exist vector_store mkdir vector_store

REM Start FastAPI backend in a new window
echo Starting FastAPI backend on http://localhost:8000 ...
start "ChatDEVA Backend" cmd /k "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for backend to start
timeout /t 5 /nobreak > nul

REM Start Streamlit frontend in a new window
echo Starting Streamlit frontend on http://localhost:8501 ...
start "ChatDEVA Frontend" cmd /k "streamlit run frontend/app.py --server.port 8501"

echo.
echo ========================================
echo   ChatDEVA is starting!
echo   Frontend : http://localhost:8501
echo   API docs : http://localhost:8000/docs
echo ========================================
echo   Default admin: username=admin password=admin123
echo   Change the admin password immediately!
echo ========================================

"""
main.py — FastAPI application entry point
------------------------------------------
Run locally:
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

Run on Railway:
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

import logging
import os
import sys

# Add backend directory to Python path for sibling imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import auth, documents, chat, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup / Shutdown ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 ChatDEVA backend starting...")
    logger.info(f"   DATABASE_URL: {'set' if settings.DATABASE_URL else 'MISSING'}")
    logger.info(f"   CHROMA_MODE:  {settings.CHROMA_MODE}")
    logger.info(f"   BACKEND_URL:  {settings.BACKEND_URL}")

    # Create upload and vector dirs if they don't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)

    init_db()
    logger.info("✅ Startup complete.")
    yield
    logger.info("👋 Shutting down.")


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="ChatDEVA API",
    description="Multi-college AI assistant backend",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
# In production, ALLOWED_ORIGINS should be your Streamlit Railway URL
# e.g. "https://chatdeva-frontend.up.railway.app"
origins = (
    settings.ALLOWED_ORIGINS.split(",")
    if settings.ALLOWED_ORIGINS != "*"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(admin.router)


# ── Health check ──────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "service": "ChatDEVA API v2",
        "chroma_mode": settings.CHROMA_MODE,
        "db": "connected",
    }

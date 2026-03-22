"""
config.py — Centralised settings
---------------------------------
Reads all configuration from environment variables.
Railway injects DATABASE_URL and PORT automatically.
All other vars must be set in Railway's Variables dashboard.
"""

import os
from dotenv import load_dotenv

# Load .env in local dev — Railway injects vars directly, so this is a no-op in prod
load_dotenv()


class Settings:
    # ── Database ──────────────────────────────────────────────────────
    # Railway auto-sets DATABASE_URL when you add a Postgres service.
    # Format: postgresql://user:pass@host:port/dbname
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chatdeva.db")

    # ── JWT ───────────────────────────────────────────────────────────
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    # ── HuggingFace ───────────────────────────────────────────────────
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # ── File uploads ──────────────────────────────────────────────────
    # On Railway, use /tmp for uploads (persistent volume optional)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/chatdeva_uploads")
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    ALLOWED_EXTENSIONS: set = {".pdf", ".docx", ".txt"}

    # ── Vector store ──────────────────────────────────────────────────
    VECTOR_STORE_DIR: str = os.getenv("VECTOR_STORE_DIR", "/tmp/chatdeva_vectors")
    # CHROMA_MODE: "local" for dev, "server" for Railway ChromaDB service
    CHROMA_MODE: str = os.getenv("CHROMA_MODE", "local")
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))

    # ── RAG ───────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    RETRIEVAL_K: int = 5
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "1.0"))
    RERANK_THRESHOLD: float = float(os.getenv("RERANK_THRESHOLD", "0.3"))

    # ── Models ────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "google/flan-t5-large")
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── URLs ──────────────────────────────────────────────────────────
    # In production: set BACKEND_URL to your Railway backend public URL
    # e.g. https://chatdeva-backend.up.railway.app
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8501"))

    # ── CORS ──────────────────────────────────────────────────────────
    # Set ALLOWED_ORIGINS to your frontend Railway URL in production
    # e.g. https://chatdeva-frontend.up.railway.app
    # Use "*" only in development
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")


settings = Settings()

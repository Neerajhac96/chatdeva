"""
config.py — Centralised settings
---------------------------------
Phase 2 changes:
  - Added GROQ_API_KEY and GROQ_MODEL
  - Removed LLM_MODEL and RERANKER_MODEL (no longer needed)
  - HF_TOKEN kept for embeddings only
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chatdeva.db")

    # ── JWT ───────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    # ── HuggingFace (embeddings only — no local LLM anymore) ──────────
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # ── Groq API (replaces local Flan-T5) ─────────────────────────────
    # Free tier: https://console.groq.com
    # Generous limits: 14,400 requests/day, ~6000 tokens/min
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    # Best free model for Q&A tasks — fast and accurate
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-8b-8192")

    # ── File uploads ──────────────────────────────────────────────────
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/chatdeva_uploads")
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    ALLOWED_EXTENSIONS: set = {".pdf", ".docx", ".txt"}

    # ── Vector store ──────────────────────────────────────────────────
    VECTOR_STORE_DIR: str = os.getenv("VECTOR_STORE_DIR", "/tmp/chatdeva_vectors")
    CHROMA_MODE: str = os.getenv("CHROMA_MODE", "local")
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))

    # ── RAG ───────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    RETRIEVAL_K: int = 5
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "1.0"))

    # ── Embedding model (still local, lightweight ~100MB) ─────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── URLs ──────────────────────────────────────────────────────────
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8501"))
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")


settings = Settings()

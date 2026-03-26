"""
rag_core.py — Phase 3: Improved RAG Quality
---------------------------------------------
What changed from Phase 2:
  - Query classification: detects doc_type from query keywords
    e.g. "exam schedule" → searches exam docs first
  - Metadata-aware retrieval: filters by doc_type when confident
  - Richer source references: filename + doc_type + upload date
  - Better Groq prompt: includes doc_type context for more focused answers
  - Fallback: if typed search returns nothing, falls back to full search

No new dependencies. Same RAM usage (~150MB).
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

import uuid
import logging
import requests
from datetime import datetime
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

import chromadb
from config import settings

logger = logging.getLogger(__name__)

# ── Singletons ────────────────────────────────────────────────────────
_embeddings: Optional[HuggingFaceEmbeddings] = None
_chroma_client: Optional[chromadb.ClientAPI] = None
_store_cache: dict[int, Chroma] = {}

LOADERS = {
    ".pdf":  PyPDFLoader,
    ".txt":  TextLoader,
    ".docx": Docx2txtLoader,
}

# ── [PHASE 3] Query → doc_type keyword mapping ────────────────────────
# Maps common student query keywords to document types
# Used to filter ChromaDB results for better precision
DOC_TYPE_KEYWORDS = {
    "syllabus":   ["syllabus", "curriculum", "subject", "course", "topics", "unit"],
    "exam":       ["exam", "examination", "schedule", "date sheet", "timetable", "test", "paper"],
    "notice":     ["notice", "announcement", "circular", "notification", "update", "news"],
    "timetable":  ["timetable", "time table", "class schedule", "lecture", "timing", "slot"],
}


def classify_query(query: str) -> Optional[str]:
    """
    Detects the most likely document type from the query.
    Returns doc_type string or None if unclear.

    Example:
      "What is the exam schedule for May?" → "exam"
      "Show me the Python syllabus"        → "syllabus"
      "Any notices about holidays?"        → "notice"
      "What is cloud computing?"           → None (general, search all)
    """
    query_lower = query.lower()
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            logger.info(f"🎯 Query classified as doc_type='{doc_type}'")
            return doc_type
    return None


# ── Embeddings ────────────────────────────────────────────────────────
def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info("🔄 Loading embedding model...")
        _embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        logger.info("✅ Embeddings ready.")
    return _embeddings


# ── ChromaDB ──────────────────────────────────────────────────────────
def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        if settings.CHROMA_MODE == "server":
            _chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST, port=settings.CHROMA_PORT
            )
        else:
            os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=settings.VECTOR_STORE_DIR)
        logger.info("✅ ChromaDB client ready.")
    return _chroma_client


def get_college_store(college_id: int) -> Chroma:
    """Returns college-isolated vector store."""
    if college_id not in _store_cache:
        collection_name = f"chatdeva_college_{college_id}"
        _store_cache[college_id] = Chroma(
            client=get_chroma_client(),
            collection_name=collection_name,
            embedding_function=get_embeddings(),
        )
        logger.info(f"✅ Vector store for college_id={college_id}")
    return _store_cache[college_id]


# ── Document processing ───────────────────────────────────────────────
def process_college_document(
    file_path: str,
    college_id: int,
    doc_type: str,
    original_name: str,
    uploader_id: int,
    uploaded_at: Optional[datetime] = None,
) -> int:
    """
    Chunks and indexes one document.
    [PHASE 3] Richer metadata attached to every chunk:
      source, doc_type, college_id, uploader_id, uploaded_at, upload_date
    upload_date is stored separately as YYYY-MM-DD for easy filtering.
    """
    now = uploaded_at or datetime.utcnow()
    metadata = {
        "source":      original_name,
        "doc_type":    doc_type,
        "college_id":  college_id,
        "uploader_id": uploader_id,
        "uploaded_at": now.strftime("%Y-%m-%d %H:%M"),
        "upload_date": now.strftime("%Y-%m-%d"),   # [PHASE 3] date-only for display
    }

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in LOADERS:
        raise ValueError(f"Unsupported file type: {ext}")

    loader = LOADERS[ext](file_path)
    docs = loader.load()
    for doc in docs:
        doc.metadata.update(metadata)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)

    if not chunks:
        logger.warning(f"No chunks from {original_name}")
        return 0

    ids = [str(uuid.uuid4()) for _ in chunks]
    store = get_college_store(college_id)
    store.add_documents(documents=chunks, ids=ids)
    logger.info(f"✅ Indexed {len(chunks)} chunks → '{original_name}' (college {college_id})")
    return len(chunks)


def delete_college_document(college_id: int, original_name: str) -> int:
    """Deletes all chunks for a document from the college's vector store."""
    try:
        client = get_chroma_client()
        collection = client.get_collection(f"chatdeva_college_{college_id}")
        results = collection.get(where={"source": original_name})
        chunk_ids = results.get("ids", [])
        if not chunk_ids:
            return 0
        collection.delete(ids=chunk_ids)
        _store_cache.pop(college_id, None)
        logger.info(f"🗑️ Deleted {len(chunk_ids)} chunks for '{original_name}'")
        return len(chunk_ids)
    except Exception as e:
        logger.error(f"Error deleting '{original_name}': {e}")
        return 0


# ── [PHASE 3] Metadata-aware retrieval ───────────────────────────────
def retrieve_docs(
    store: Chroma,
    query: str,
    doc_type: Optional[str],
    k: int,
) -> list[Document]:
    """
    Retrieves top-k chunks with optional doc_type filtering.

    Strategy:
      1. If doc_type detected → search with metadata filter first
      2. If filtered search returns < 2 results → fallback to full search
      3. Return best results either way

    This means:
      - "exam schedule" → searches exam docs first (more precise)
      - "what is OOP?" → searches all docs (no type filter)
    """
    # Try typed search first if doc_type was detected
    if doc_type:
        try:
            typed_results = store.similarity_search_with_score(
                query,
                k=k,
                filter={"doc_type": doc_type},
            )
            if len(typed_results) >= 2:
                logger.info(f"✅ Typed retrieval: {len(typed_results)} results (doc_type={doc_type})")
                return [doc for doc, _ in typed_results]
            else:
                logger.info(f"⚠️ Typed retrieval returned {len(typed_results)} — falling back to full search")
        except Exception as e:
            logger.warning(f"Typed search failed: {e} — falling back")

    # Full search (no filter)
    results = store.similarity_search_with_score(query, k=k)
    logger.info(f"📄 Full retrieval: {len(results)} results")
    return [doc for doc, _ in results]


# ── Groq API ──────────────────────────────────────────────────────────
def call_groq(context: str, question: str, doc_type: Optional[str] = None) -> str:
    """
    [PHASE 3] Enhanced Groq prompt includes doc_type context.
    Tells the LLM what kind of document it's reading for better answers.
    """
    if not settings.GROQ_API_KEY:
        return "Configuration error: AI service not configured. Please contact admin."

    # [PHASE 3] Type-aware system prompt
    type_hint = f" You are reading {doc_type} documents." if doc_type else ""

    system_prompt = (
        "You are a helpful academic assistant for college students."
        f"{type_hint} "
        "Answer questions using ONLY the provided context. "
        "If the answer is not in the context, say exactly: "
        "'The answer is not available in the provided documents.' "
        "Be concise, clear, and helpful. "
        "Use bullet points for lists when appropriate."
    )

    user_prompt = f"""Context from college documents:
{context}

Question: {question}

Provide a clear, helpful answer based only on the context above:"""

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens": 512,
        "temperature": 0.1,
    }

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        logger.error("Groq API timeout")
        return "Request timed out. Please try again."
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return "AI service temporarily unavailable. Please try again."


# ── Main query function ───────────────────────────────────────────────
def get_answer(query: str, college_id: int) -> dict:
    """
    Phase 3 RAG pipeline:
      1. Classify query     → detect doc_type from keywords
      2. Similarity gate    → cheap relevance check
      3. Typed retrieval    → filter by doc_type if detected, fallback to full
      4. Groq API           → type-aware prompt for better answers
      5. Rich sources       → filename + doc_type + upload date
    """
    store = get_college_store(college_id)

    # ── Step 1: Classify query ────────────────────────────────────────
    doc_type = classify_query(query)

    # ── Step 2: Similarity gate ───────────────────────────────────────
    try:
        docs_with_scores = store.similarity_search_with_score(
            query, k=settings.RETRIEVAL_K
        )
    except Exception as e:
        logger.error(f"ChromaDB error: {e}")
        return {"answer": "⚠️ Search error. Please try again.", "sources": []}

    if not docs_with_scores:
        return {
            "answer": "The answer is not available in the provided documents.",
            "sources": [],
        }

    best_score = docs_with_scores[0][1]
    logger.info(f"Best score: {best_score:.4f} (threshold={settings.SIMILARITY_THRESHOLD})")

    if best_score > settings.SIMILARITY_THRESHOLD:
        return {
            "answer": (
                "The answer is not available in the provided documents. "
                "Please ensure the relevant study material has been uploaded."
            ),
            "sources": [],
        }

    # ── Step 3: Typed retrieval ───────────────────────────────────────
    top_docs = retrieve_docs(store, query, doc_type, settings.RETRIEVAL_K)
    if not top_docs:
        top_docs = [doc for doc, _ in docs_with_scores]

    # Truncate chunks to prevent Groq 400 Bad Request (context too long)
    chunks = [doc.page_content[:400] for doc in top_docs]
    context = "\n\n".join(chunks)[:3000]
    logger.info(f"Context length: {len(context)} chars")

    # ── Step 4: Groq API with type context ───────────────────────────
    logger.info(f"🤖 Calling Groq (doc_type={doc_type})...")
    answer = call_groq(context, query, doc_type)

    # ── Step 5: Rich source metadata ─────────────────────────────────
    seen = set()
    sources = []
    for doc in top_docs:
        m = doc.metadata
        fname = m.get("source", "Unknown")
        if fname not in seen:
            seen.add(fname)
            sources.append({
                "filename":    fname,
                "doc_type":    m.get("doc_type", "other"),
                "uploaded_at": m.get("uploaded_at", ""),
                "upload_date": m.get("upload_date", ""),   # [PHASE 3]
            })

    logger.info(f"✅ Answer ready. Sources: {[s['filename'] for s in sources]}")
    return {"answer": answer, "sources": sources}

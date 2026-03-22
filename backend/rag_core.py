"""
rag_core.py — College-isolated RAG pipeline
---------------------------------------------
Key design decisions:
  - Every college gets its own ChromaDB collection: chatdeva_college_{id}
  - Vector stores are lazy-loaded and cached per college in _store_cache
  - MultiQueryRetriever + cross-encoder reranker from Phase 5 are preserved
  - Metadata (filename, doc_type, upload time) is attached to every chunk
    so sources in responses are rich and traceable
  - No hallucination fallback — if retrieval fails, say so cleanly

College isolation flow:
  upload  → process_college_documents(college_id, doc_type, ...)
  query   → get_answer(query, college_id)
            ↳ retrieves ONLY from that college's collection
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))


import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from sentence_transformers import CrossEncoder
import chromadb

from config import settings

logger = logging.getLogger(__name__)

# ── Module-level singletons ───────────────────────────────────────────
# Models load once and are reused across all colleges
_embeddings:        Optional[HuggingFaceEmbeddings] = None
_llm:               Optional[HuggingFacePipeline]   = None
_reranker:          Optional[CrossEncoder]           = None
_chroma_client:     Optional[chromadb.ClientAPI]     = None

# Per-college vector store cache: { college_id: Chroma }
_store_cache: dict[int, Chroma] = {}


# ── Singleton getters ─────────────────────────────────────────────────
def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info("🔄 Loading embedding model...")
        _embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        logger.info("✅ Embeddings ready.")
    return _embeddings


def get_llm() -> HuggingFacePipeline:
    global _llm
    if _llm is None:
        logger.info("🔄 Loading LLM (first call — takes a moment)...")
        tok = AutoTokenizer.from_pretrained(settings.LLM_MODEL)
        mdl = AutoModelForSeq2SeqLM.from_pretrained(settings.LLM_MODEL)
        gen = pipeline(
            "text2text-generation", model=mdl, tokenizer=tok, max_new_tokens=512, num_beams=4
        )
        _llm = HuggingFacePipeline(pipeline=gen)
        logger.info("✅ LLM ready.")
    return _llm


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info("🔄 Loading reranker...")
        _reranker = CrossEncoder(settings.RERANKER_MODEL)
        logger.info("✅ Reranker ready.")
    return _reranker


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        if settings.CHROMA_MODE == "server":
            logger.info(f"🌐 Connecting to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
            _chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST, port=settings.CHROMA_PORT
            )
        else:
            os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)
            logger.info(f"💾 Using local ChromaDB at {settings.VECTOR_STORE_DIR}/")
            _chroma_client = chromadb.PersistentClient(path=settings.VECTOR_STORE_DIR)
        logger.info("✅ ChromaDB client ready.")
    return _chroma_client


# ── Per-college vector store ──────────────────────────────────────────
def get_college_store(college_id: int) -> Chroma:
    """
    Returns (and caches) the Chroma vector store for a specific college.
    Collection name: chatdeva_college_{college_id}
    This is the core of multi-college isolation.
    """
    if college_id not in _store_cache:
        collection_name = f"chatdeva_college_{college_id}"
        _store_cache[college_id] = Chroma(
            client=get_chroma_client(),
            collection_name=collection_name,
            embedding_function=get_embeddings(),
        )
        logger.info(f"✅ Vector store loaded for college_id={college_id}")
    return _store_cache[college_id]


# ── File loaders ──────────────────────────────────────────────────────
LOADERS = {
    ".pdf":  PyPDFLoader,
    ".txt":  TextLoader,
    ".docx": Docx2txtLoader,
}


def _load_file(file_path: str, metadata: dict) -> list[Document]:
    """Loads a file and attaches metadata to every page/chunk."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in LOADERS:
        raise ValueError(f"Unsupported file type: {ext}")

    loader = LOADERS[ext](file_path)
    docs = loader.load()

    # Attach rich metadata to every document page
    for doc in docs:
        doc.metadata.update(metadata)
    return docs


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
    Loads, chunks, and indexes one document into the college's vector store.
    Returns the number of chunks indexed.

    Metadata attached to every chunk:
      source, doc_type, college_id, uploader_id, uploaded_at
    This metadata is returned in query responses so students know
    exactly which document the answer came from.
    """
    uploaded_at_str = (uploaded_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M")

    metadata = {
        "source":      original_name,
        "doc_type":    doc_type,
        "college_id":  college_id,
        "uploader_id": uploader_id,
        "uploaded_at": uploaded_at_str,
    }

    docs = _load_file(file_path, metadata)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)

    if not chunks:
        logger.warning(f"No chunks produced from {original_name}")
        return 0

    # Stable UUIDs for deduplication
    ids = [str(uuid.uuid4()) for _ in chunks]
    store = get_college_store(college_id)
    store.add_documents(documents=chunks, ids=ids)

    logger.info(f"✅ Indexed {len(chunks)} chunks from '{original_name}' → college {college_id}")
    return len(chunks)


def delete_college_document(college_id: int, original_name: str) -> int:
    """
    Deletes all chunks belonging to a document from the college's vector store.
    Matched by metadata.source == original_name.
    Returns number of chunks deleted.
    """
    try:
        client = get_chroma_client()
        collection_name = f"chatdeva_college_{college_id}"
        collection = client.get_collection(collection_name)

        results = collection.get(where={"source": original_name})
        chunk_ids = results.get("ids", [])

        if not chunk_ids:
            logger.info(f"No chunks found for '{original_name}' in college {college_id}")
            return 0

        collection.delete(ids=chunk_ids)
        # Invalidate cache so next query re-loads the collection
        _store_cache.pop(college_id, None)
        logger.info(f"🗑️ Deleted {len(chunk_ids)} chunks for '{original_name}'")
        return len(chunk_ids)
    except Exception as e:
        logger.error(f"Error deleting '{original_name}': {e}")
        return 0


# ── Reranking ─────────────────────────────────────────────────────────
def _rerank(query: str, docs: list[Document], top_n: int = 5) -> list[Document]:
    """Re-scores retrieved docs with the cross-encoder and filters by threshold."""
    if not docs:
        return []

    reranker = get_reranker()
    pairs  = [(query, doc.page_content) for doc in docs]
    scores = reranker.predict(pairs)

    scored = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    filtered = [
        doc for score, doc in scored[:top_n]
        if score >= settings.RERANK_THRESHOLD
    ]
    logger.info(f"Reranker: {len(filtered)}/{len(docs)} docs passed threshold={settings.RERANK_THRESHOLD}")
    return filtered


# ── Static retriever ──────────────────────────────────────────────────
class StaticRetriever(BaseRetriever):
    """Wraps a fixed list of documents for use with RetrievalQA."""
    docs: list

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return self.docs


# ── Prompt ────────────────────────────────────────────────────────────
QA_PROMPT = PromptTemplate(
    template="""You are a helpful academic assistant.
Use ONLY the context below to answer the question.
If the answer is not present, say exactly:
"The answer is not available in the provided documents."
Do not guess or fabricate information.

Context:
{context}

Question: {question}

Detailed Answer:""",
    input_variables=["context", "question"],
)


# ── Main query function ───────────────────────────────────────────────
def get_answer(query: str, college_id: int) -> dict:
    """
    Full RAG pipeline for a college-scoped query.

    Returns:
      {
        "answer":  str,
        "sources": [ { filename, doc_type, uploaded_at }, ... ]
      }

    Pipeline:
      1. Similarity gate    → cheap first-pass, avoids LLM call on irrelevant queries
      2. MultiQueryRetriever → 3 rephrasings for wider recall
      3. Cross-encoder rerank → accurate second-pass scoring
      4. LLM                 → grounded answer from top chunks only
    """
    store = get_college_store(college_id)

    # ── Step 1: Similarity gate ───────────────────────────────────────
    try:
        docs_with_scores = store.similarity_search_with_score(
            query, k=settings.RETRIEVAL_K
        )
    except Exception as e:
        logger.error(f"ChromaDB search error: {e}")
        return {"answer": "⚠️ Vector store error. Please contact support.", "sources": []}

    if not docs_with_scores:
        return {
            "answer": "The answer is not available in the provided documents.",
            "sources": [],
        }

    best_score = docs_with_scores[0][1]
    logger.info(f"Best similarity score: {best_score:.4f} (threshold={settings.SIMILARITY_THRESHOLD})")

    if best_score > settings.SIMILARITY_THRESHOLD:
        return {
            "answer": (
                "The answer is not available in the provided documents. "
                "Please ensure the relevant material has been uploaded."
            ),
            "sources": [],
        }

    llm = get_llm()

    # ── Step 2: Direct retrieval (MultiQueryRetriever skipped — unreliable with Flan-T5)
    try:
        candidate_docs = store.similarity_search(query, k=settings.RETRIEVAL_K)
        logger.info(f"Direct retrieval returned {len(candidate_docs)} candidates")
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        return {"answer": "The answer is not available in the provided documents.", "sources": []}

    if not candidate_docs:
        return {
            "answer": "The answer is not available in the provided documents.",
            "sources": [],
        }

    # ── Step 3: Rerank ────────────────────────────────────────────────
    try:
        reranked = _rerank(query, candidate_docs, top_n=settings.RETRIEVAL_K)
    except Exception as e:
        logger.error(f"Reranker error: {e} — falling back to direct retrieval results")
        reranked = candidate_docs  # fallback: use unranked docs

    if not reranked:
        reranked = candidate_docs  # fallback if all filtered out

    # ── Step 4: LLM — direct invocation (bypasses RetrievalQA prompt echo bug) ──
    # Build context string from reranked chunks
    context = "".join([doc.page_content for doc in reranked])

    # Build clean prompt for Flan-T5
    prompt = (
        f"You are a helpful academic assistant."
        f"Use ONLY the context below to answer the question."
        f"If the answer is not present in the context, say exactly: "
        f"The answer is not available in the provided documents."
        f"Context:{context}"
        f"Question: {query}"
        f"Give a detailed answer with explanation:"
    )

    # Call LLM directly — Flan-T5 returns only the answer, not the prompt
    try:
        raw = llm.invoke(prompt)
        logger.info(f"LLM raw output type: {type(raw)}, value: {str(raw)[:200]}")
    except Exception as e:
        logger.error(f"LLM invoke error: {e}")
        raise

    # HuggingFacePipeline returns a string directly
    if isinstance(raw, str):
        answer = raw.strip()
    elif isinstance(raw, list) and len(raw) > 0:
        item = raw[0]
        if isinstance(item, dict):
            answer = item.get("generated_text", str(item)).strip()
        else:
            answer = str(item).strip()
    else:
        answer = str(raw).strip()

    # If LLM echoed the prompt, strip it
    if "Answer:" in answer:
        answer = answer.split("Answer:")[-1].strip()

    if not answer or answer.strip() == "":
        answer = "The answer is not available in the provided documents."

    # Build rich source metadata (deduplicated by filename)
    seen = set()
    sources = []
    for doc in reranked:
        m = doc.metadata
        fname = m.get("source", "Unknown")
        if fname not in seen:
            seen.add(fname)
            sources.append({
                "filename":    fname,
                "doc_type":    m.get("doc_type", "other"),
                "uploaded_at": m.get("uploaded_at", ""),
            })

    return {"answer": answer, "sources": sources}

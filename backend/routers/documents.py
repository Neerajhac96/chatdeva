"""
routers/documents.py — Document management endpoints
------------------------------------------------------
All endpoints require ADMIN or STAFF role (require_staff dependency).
Students cannot access any of these routes — enforced at API level.

Endpoints:
  POST   /documents/upload         → upload + index a document
  GET    /documents/               → list documents for current college
  DELETE /documents/{doc_id}       → delete document + remove from vector store
  POST   /documents/{doc_id}/index → re-index an already-uploaded document
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))


import os
import logging
from datetime import datetime

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, status
)
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User, Document, DocType, AuditLog
from schemas import DocumentResponse
from dependencies import require_staff, require_admin, assert_same_college
from rag_core import process_college_document, delete_college_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


# ── Helpers ───────────────────────────────────────────────────────────
def _college_upload_dir(college_id: int) -> str:
    """Returns (and creates) the upload directory for a college."""
    path = os.path.join(settings.UPLOAD_DIR, str(college_id))
    os.makedirs(path, exist_ok=True)
    return path


def _validate_file(file: UploadFile):
    """Validates file extension and size."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )


def _log_audit(db, user_id, action, detail=None):
    db.add(AuditLog(user_id=user_id, action=action, detail=detail))
    db.commit()


# ── Upload ────────────────────────────────────────────────────────────
@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file:       UploadFile = File(...),
    doc_type:   str        = Form(default="other"),
    db:         Session    = Depends(get_db),
    current_user: User     = Depends(require_staff),   # ADMIN or STAFF only
):
    """
    Uploads a document, saves it to disk, and indexes it into ChromaDB.

    Steps:
      1. Validate file type + size
      2. Save to uploads/{college_id}/
      3. Create Document record in DB (is_indexed=False)
      4. Process through RAG pipeline (chunking + embedding)
      5. Update is_indexed=True
    """
    _validate_file(file)

    # Validate doc_type
    try:
        doc_type_enum = DocType(doc_type)
    except ValueError:
        doc_type_enum = DocType.other

    # Read file content and check size
    content = await file.read()
    size_kb = len(content) / 1024
    if size_kb > settings.MAX_UPLOAD_MB * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_MB}MB",
        )

    # Build unique filename to prevent overwrites
    upload_dir = _college_upload_dir(current_user.college_id)
    base, ext  = os.path.splitext(file.filename)
    filename   = file.filename
    file_path  = os.path.join(upload_dir, filename)
    counter    = 1
    while os.path.exists(file_path):
        filename  = f"{base}_{counter}{ext}"
        file_path = os.path.join(upload_dir, filename)
        counter  += 1

    # Write to disk
    with open(file_path, "wb") as f:
        f.write(content)

    # Save DB record
    doc = Document(
        filename=filename,
        original_name=file.filename,
        doc_type=doc_type_enum,
        file_size_kb=round(size_kb, 2),
        is_indexed=False,
        uploader_id=current_user.id,
        college_id=current_user.college_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Index into college-isolated vector store
    try:
        n_chunks = process_college_document(
            file_path=file_path,
            college_id=current_user.college_id,
            doc_type=doc_type_enum.value,
            original_name=file.filename,
            uploader_id=current_user.id,
            uploaded_at=doc.created_at,
        )
        doc.is_indexed = True
        db.commit()
        logger.info(f"✅ Indexed '{file.filename}' → {n_chunks} chunks")
    except Exception as e:
        logger.error(f"Indexing failed for '{file.filename}': {e}")
        # Document saved but not indexed — admin can retry via /index endpoint
        raise HTTPException(
            status_code=500,
            detail=f"File uploaded but indexing failed: {str(e)}",
        )

    _log_audit(db, current_user.id, "document.upload",
               detail=f"doc_id={doc.id}, file={file.filename}")
    return doc


# ── List ──────────────────────────────────────────────────────────────
@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_staff),   # STUDENTS cannot access
):
    """
    Returns all documents for the current user's college.
    Scoped by college_id — no cross-college leakage possible.
    """
    return (
        db.query(Document)
        .filter_by(college_id=current_user.college_id)
        .order_by(Document.created_at.desc())
        .all()
    )


# ── Delete ────────────────────────────────────────────────────────────
@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id:       int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_staff),
):
    """
    Deletes a document:
      1. Validates it belongs to the current user's college
      2. Removes chunks from ChromaDB
      3. Deletes the physical file
      4. Removes the DB record
    """
    doc = db.query(Document).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # College isolation check — cannot delete another college's doc
    assert_same_college(current_user, doc.college_id)

    # Remove from vector store
    n_deleted = delete_college_document(current_user.college_id, doc.original_name)
    logger.info(f"Removed {n_deleted} chunks from vector store")

    # Delete physical file
    upload_dir = _college_upload_dir(current_user.college_id)
    file_path  = os.path.join(upload_dir, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    _log_audit(db, current_user.id, "document.delete",
               detail=f"doc_id={doc_id}, file={doc.original_name}")

    db.delete(doc)
    db.commit()
    # 204 No Content — no response body


# ── Re-index ──────────────────────────────────────────────────────────
@router.post("/{doc_id}/index", response_model=DocumentResponse)
def reindex_document(
    doc_id:       int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_staff),
):
    """
    Re-indexes an already-uploaded document.
    Useful if indexing failed during upload, or after model changes.
    """
    doc = db.query(Document).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    assert_same_college(current_user, doc.college_id)

    upload_dir = _college_upload_dir(current_user.college_id)
    file_path  = os.path.join(upload_dir, doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file not found on disk.")

    # Delete existing chunks first to avoid duplicates
    delete_college_document(current_user.college_id, doc.original_name)

    n_chunks = process_college_document(
        file_path=file_path,
        college_id=current_user.college_id,
        doc_type=doc.doc_type.value,
        original_name=doc.original_name,
        uploader_id=doc.uploader_id,
        uploaded_at=doc.created_at,
    )
    doc.is_indexed = True
    db.commit()
    db.refresh(doc)

    logger.info(f"Re-indexed '{doc.original_name}' → {n_chunks} chunks")
    return doc

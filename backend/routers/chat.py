"""
routers/chat.py — Chat session and message endpoints
------------------------------------------------------
All endpoints require authentication (any role).
Students see only their own data. Admins see all (via /admin routes).

Endpoints:
  POST   /chat/sessions              → create new chat session
  GET    /chat/sessions              → list user's sessions
  DELETE /chat/sessions/{id}         → delete a session + its messages
  DELETE /chat/sessions              → clear ALL user's sessions
  GET    /chat/sessions/{id}/messages → get messages for a session
  POST   /chat/ask                   → send a query, get RAG answer
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))


import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User, ChatSession, ChatMessage
from schemas import (
    ChatRequest, ChatResponse, SessionCreate,
    SessionResponse, MessageResponse, SourceMeta,
)
from dependencies import get_current_user
from rag_core import get_answer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Sessions ──────────────────────────────────────────────────────────
@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    payload:      SessionCreate = SessionCreate(),
    db:           Session       = Depends(get_db),
    current_user: User          = Depends(get_current_user),
):
    """Creates a new chat session (equivalent to 'New Chat' button)."""
    session = ChatSession(
        user_id=current_user.id,
        college_id=current_user.college_id,
        title=payload.title or "New Chat",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"Session {session.id} created for user {current_user.id}")
    return session


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Returns all chat sessions for the current user, newest first."""
    return (
        db.query(ChatSession)
        .filter_by(user_id=current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id:   int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Deletes a single session and all its messages."""
    session = db.query(ChatSession).filter_by(
        id=session_id, user_id=current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete(session)   # cascade deletes messages
    db.commit()


@router.delete("/sessions", status_code=204)
def clear_all_sessions(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Deletes ALL sessions (and messages) for the current user."""
    sessions = db.query(ChatSession).filter_by(user_id=current_user.id).all()
    for s in sessions:
        db.delete(s)
    db.commit()
    logger.info(f"Cleared all sessions for user {current_user.id}")


# ── Messages ──────────────────────────────────────────────────────────
@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def get_session_messages(
    session_id:   int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Returns all messages for a session.
    Enforces ownership — users can only read their own sessions.
    """
    session = db.query(ChatSession).filter_by(
        id=session_id, user_id=current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session.messages


# ── Ask ───────────────────────────────────────────────────────────────
@router.post("/ask", response_model=ChatResponse)
def ask(
    payload:      ChatRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Main chat endpoint. Accepts a query, runs the RAG pipeline,
    returns the answer + sources, and persists both messages to DB.

    College isolation: get_answer() is called with current_user.college_id
    so the vector store searched is always the user's own college's store.
    No cross-college retrieval is possible.
    """
    # Validate session belongs to this user
    session = db.query(ChatSession).filter_by(
        id=payload.session_id, user_id=current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # [PHASE 8] Usage limit check — students only, admins/staff unlimited
    if current_user.role.value == "student":
        from models import College
        from datetime import date
        college = db.query(College).filter_by(id=current_user.college_id).first()
        monthly_limit = college.monthly_limit if college else 100

        # Reset counter if new month
        current_month = date.today().strftime("%Y-%m")
        if current_user.last_reset_date != current_month:
            current_user.questions_this_month = 0
            current_user.last_reset_date = current_month
            db.commit()

        # Block if limit reached
        if current_user.questions_this_month >= monthly_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Monthly limit of {monthly_limit} questions reached. "                       f"Please contact your college admin to upgrade the plan."
            )

        # Increment counter
        current_user.questions_this_month += 1
        db.commit()

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.query,
        sources="[]",
    )
    db.add(user_msg)
    db.commit()

    # Run college-isolated RAG
    try:
        result  = get_answer(payload.query, current_user.college_id)
        answer  = result["answer"]
        sources = result["sources"]   # list of dicts
    except Exception as e:
        logger.error(f"RAG error for user {current_user.id}: {e}")
        answer  = "⚠️ An error occurred while processing your question. Please try again."
        sources = []

    # Auto-update session title from first user query (max 60 chars)
    if session.title == "New Chat":
        session.title = payload.query[:60]
        db.commit()

    # Save assistant message with sources as JSON
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources),
    )
    db.add(assistant_msg)
    db.commit()

    # Build response
    source_metas = [
        SourceMeta(
            filename=s.get("filename", ""),
            doc_type=s.get("doc_type", "other"),
            uploaded_at=s.get("uploaded_at", ""),
        )
        for s in sources
    ]

    return ChatResponse(
        answer=answer,
        sources=source_metas,
        session_id=session.id,
    )

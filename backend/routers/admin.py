"""
routers/admin.py — Admin-only management endpoints
----------------------------------------------------
All endpoints require ADMIN role (require_admin dependency).
Admins are scoped to their own college — cannot manage other colleges.

Endpoints:
  POST  /admin/users              → create admin/staff account
  GET   /admin/users              → list all users in college
  PATCH /admin/users/{id}/role    → change a user's role
  DELETE /admin/users/{id}        → deactivate (soft delete) a user
  GET   /admin/chats              → view all chat sessions in college
  GET   /admin/chats/{session_id} → view messages in any session
  GET   /admin/audit              → view audit log for college
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))


import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import bcrypt

from config import settings
from database import get_db
from models import User, UserRole, ChatSession, ChatMessage, AuditLog
from schemas import (
    UserResponse, RoleUpdateRequest,
    SessionResponse, MessageResponse, AuditLogResponse,
)
from dependencies import require_admin, assert_same_college

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ── User management ───────────────────────────────────────────────────
@router.post("/users", response_model=UserResponse, status_code=201)
def create_privileged_user(
    username:   str,
    password:   str,
    role:       UserRole,
    db:         Session = Depends(get_db),
    current_user: User  = Depends(require_admin),
):
    """
    Admin-only: creates admin or staff accounts within the same college.
    Students self-register via /auth/register.
    """
    if role == UserRole.student:
        raise HTTPException(
            status_code=400,
            detail="Use /auth/register for student accounts."
        )
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password too short (min 6 chars).")

    existing = db.query(User).filter_by(
        username=username, college_id=current_user.college_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken.")

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    user = User(
        username=username,
        password_hash=password_hash,
        role=role,
        college_id=current_user.college_id,
    )
    db.add(user)

    db.add(AuditLog(
        user_id=current_user.id,
        action="admin.user.create",
        detail=f"created {role.value} '{username}' in college {current_user.college_id}",
    ))
    db.commit()
    db.refresh(user)
    logger.info(f"Admin {current_user.username} created {role.value}: {username}")
    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_admin),
):
    """Returns all users in the admin's college."""
    return (
        db.query(User)
        .filter_by(college_id=current_user.college_id)
        .order_by(User.created_at)
        .all()
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id:  int,
    payload:  RoleUpdateRequest,
    db:       Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Changes a user's role. Admin cannot demote themselves."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role.")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # College isolation
    assert_same_college(current_user, user.college_id)

    old_role   = user.role
    user.role  = payload.new_role
    db.add(AuditLog(
        user_id=current_user.id,
        action="admin.user.role_change",
        detail=f"user_id={user_id} {old_role}→{payload.new_role}",
    ))
    db.commit()
    db.refresh(user)
    logger.info(f"Role changed: user {user_id} {old_role}→{payload.new_role}")
    return user


@router.delete("/users/{user_id}", status_code=204)
def deactivate_user(
    user_id:      int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_admin),
):
    """
    Soft-deletes a user by setting is_active=False.
    Preserves chat history and audit trail.
    Hard delete is intentionally not exposed to prevent data loss.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself.")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    assert_same_college(current_user, user.college_id)

    user.is_active = False
    db.add(AuditLog(
        user_id=current_user.id,
        action="admin.user.deactivate",
        detail=f"deactivated user_id={user_id}",
    ))
    db.commit()
    logger.info(f"User {user_id} deactivated by admin {current_user.id}")


# ── Chat monitoring ───────────────────────────────────────────────────
@router.get("/chats", response_model=list[SessionResponse])
def list_all_sessions(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_admin),
):
    """Returns all chat sessions in the admin's college (for monitoring)."""
    return (
        db.query(ChatSession)
        .filter_by(college_id=current_user.college_id)
        .order_by(ChatSession.created_at.desc())
        .limit(200)
        .all()
    )


@router.get("/chats/{session_id}", response_model=list[MessageResponse])
def get_any_session_messages(
    session_id:   int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_admin),
):
    """Returns messages in any session within the admin's college."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    assert_same_college(current_user, session.college_id)
    return session.messages


# ── Audit log ─────────────────────────────────────────────────────────
@router.get("/audit", response_model=list[AuditLogResponse])
def get_audit_log(
    limit:        int     = 100,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_admin),
):
    """
    Returns the most recent audit log entries for users in this college.
    Covers: logins, uploads, deletes, role changes.
    """
    # Get all user IDs in this college
    college_user_ids = [
        u.id for u in
        db.query(User.id).filter_by(college_id=current_user.college_id).all()
    ]
    return (
        db.query(AuditLog)
        .filter(AuditLog.user_id.in_(college_user_ids))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )

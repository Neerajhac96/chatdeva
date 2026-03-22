"""
dependencies.py — FastAPI dependencies for auth + role enforcement
-------------------------------------------------------------------
Every protected route injects one of these:

  get_current_user   → any authenticated user
  require_admin      → admin only
  require_staff      → admin or staff
  require_student    → student only (e.g. blocks admin from student endpoints)

Usage in a route:
  @router.get("/docs")
  def list_docs(user: User = Depends(require_staff), db: Session = Depends(get_db)):
      ...

The college_id on the token is used throughout the app to scope
every DB query — this is how multi-college isolation is enforced
at the API level, not just the UI level.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))


import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from config import settings
from database import get_db
from models import User, UserRole

logger = logging.getLogger(__name__)

# FastAPI's built-in Bearer token extractor
bearer_scheme = HTTPBearer()


# ── Token decode ──────────────────────────────────────────────────────
def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT.
    Raises HTTP 401 if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Base dependency ───────────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts and validates the JWT from the Authorization header.
    Returns the full User ORM object.
    Raises 401 if token is invalid, 403 if account is inactive.
    """
    payload = decode_token(credentials.credentials)

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user ID.",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return user


# ── Role guards ───────────────────────────────────────────────────────
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allows only ADMIN. Used for destructive or system-level operations."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """
    Allows ADMIN or STAFF.
    Used for document upload/delete/index — staff can manage docs
    but cannot manage users or colleges.
    """
    if current_user.role not in (UserRole.admin, UserRole.staff):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Staff access required.",
        )
    return current_user


def require_student(current_user: User = Depends(get_current_user)) -> User:
    """
    Allows only STUDENT.
    Used for endpoints that should not be accessible to admins
    (e.g. submitting a student feedback form).
    Currently unused but included for completeness.
    """
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access only.",
        )
    return current_user


# ── College isolation helper ──────────────────────────────────────────
def assert_same_college(user: User, college_id: int):
    """
    Raises 403 if the user is trying to access another college's data.
    Called inside route handlers before any DB query.

    Example:
        assert_same_college(current_user, document.college_id)
    """
    if user.college_id != college_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cross-college data access is not permitted.",
        )

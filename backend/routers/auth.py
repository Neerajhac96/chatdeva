"""
routers/auth.py — Authentication endpoints
-------------------------------------------
Endpoints:
  POST /auth/register  → create new account
  POST /auth/login     → get JWT token
  GET  /auth/me        → get current user info
  POST /auth/colleges  → create a college (admin only, for onboarding)
  GET  /auth/colleges  → list all colleges (public, for registration dropdown)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))


import logging
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import jwt

from config import settings
from database import get_db
from models import User, College, UserRole, AuditLog
from schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    UserResponse, CollegeResponse, CollegeCreate,
    CollegeRegisterRequest, UsageResponse,
)
from dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Helpers ───────────────────────────────────────────────────────────
def create_access_token(user: User) -> str:
    """
    Creates a signed JWT containing:
      sub        → user ID (string, standard JWT claim)
      username   → for display without an extra DB call
      role       → for frontend role-based rendering
      college_id → for data isolation enforcement
      exp        → expiry timestamp
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub":        str(user.id),
        "username":   user.username,
        "role":       user.role.value,
        "college_id": user.college_id,
        "exp":        expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _log_audit(db: Session, user_id: int | None, action: str,
               detail: str = None, ip: str = None):
    """Helper to write an audit log entry."""
    log = AuditLog(user_id=user_id, action=action, detail=detail, ip_address=ip)
    db.add(log)
    db.commit()


# ── Colleges ──────────────────────────────────────────────────────────
@router.get("/colleges", response_model=list[CollegeResponse])
def list_colleges(db: Session = Depends(get_db)):
    """
    Public endpoint — returns all colleges.
    Used to populate the college dropdown on the registration form.
    """
    return db.query(College).all()


@router.post("/colleges", response_model=CollegeResponse, status_code=201)
def create_college(
    payload: CollegeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin only — registers a new college in the system."""
    existing = db.query(College).filter_by(code=payload.code.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="College code already exists.")

    college = College(name=payload.name, code=payload.code.upper())
    db.add(college)
    db.commit()
    db.refresh(college)
    logger.info(f"College created: {college.code} by user {current_user.id}")
    return college


# ── Register ──────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Creates a new user account.

    Role rules:
      - Anyone can self-register as a student.
      - Only an existing admin can create admin/staff accounts.
        (Enforced by checking the Authorization header if role != student.)
    """
    # Validate college exists
    college = db.query(College).filter_by(id=payload.college_id).first()
    if not college:
        raise HTTPException(status_code=400, detail="College not found.")

    # Check username uniqueness within the college
    existing = db.query(User).filter_by(
        username=payload.username,
        college_id=payload.college_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken.")

    # Only admin can create admin/staff accounts
    if payload.role in (UserRole.admin, UserRole.staff):
        raise HTTPException(
            status_code=403,
            detail="Admin/staff accounts must be created by an existing admin "
                   "via the /admin/users endpoint.",
        )

    password_hash = bcrypt.hashpw(
        payload.password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    user = User(
        username=payload.username,
        password_hash=password_hash,
        role=payload.role,
        college_id=payload.college_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _log_audit(db, user.id, "auth.register",
               detail=f"username={user.username}",
               ip=request.client.host)
    logger.info(f"✅ Registered: {user.username} (college={college.code})")
    return user


# ── Login ─────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticates user credentials and returns a JWT.

    Timing-safe: always runs bcrypt.checkpw even if the user doesn't
    exist, preventing username enumeration via response time.
    """
    user = db.query(User).filter_by(username=payload.username).first()

    # Always run checkpw — dummy hash if user not found (timing safety)
    stored_hash = user.password_hash.encode("utf-8") if user else bcrypt.hashpw(b"x", bcrypt.gensalt())
    password_matches = bcrypt.checkpw(payload.password.encode("utf-8"), stored_hash)

    if not user or not password_matches:
        _log_audit(db, None, "auth.login.failed",
                   detail=f"username={payload.username}",
                   ip=request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    token = create_access_token(user)
    _log_audit(db, user.id, "auth.login",
               detail=f"role={user.role.value}",
               ip=request.client.host)
    logger.info(f"✅ Login: {user.username}")
    return TokenResponse(access_token=token)


# ── Me ────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the currently authenticated user's profile."""
    return current_user


# ── [PHASE 8] College self-registration ──────────────────────────────
@router.post("/colleges/register", response_model=dict, status_code=201)
def register_college(
    payload: "CollegeRegisterRequest",
    db: Session = Depends(get_db),
):
    """
    [PHASE 8] Public endpoint — any college can self-register.
    Creates:
      1. A new college (free plan, 100 questions/student/month)
      2. An admin account for that college

    This is the SaaS onboarding flow — no manual setup needed.
    """
    # Check college code not taken
    if db.query(College).filter_by(code=payload.code.upper()).first():
        raise HTTPException(status_code=400, detail="College code already exists.")

    # Check admin username not taken
    if db.query(User).filter_by(username=payload.admin_username).first():
        raise HTTPException(status_code=400, detail="Admin username already taken.")

    if len(payload.admin_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    # Create college
    college = College(
        name=payload.name,
        code=payload.code.upper(),
        contact_email=payload.contact_email,
    )
    db.add(college)
    db.commit()
    db.refresh(college)

    # Create admin for this college
    password_hash = bcrypt.hashpw(
        payload.admin_password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    admin = User(
        username=payload.admin_username,
        password_hash=password_hash,
        role=UserRole.admin,
        college_id=college.id,
    )
    db.add(admin)
    db.commit()

    logger.info(f"✅ College registered: {college.code} | Admin: {admin_username}")
    return {
        "message": "College registered successfully!",
        "college_id": college.id,
        "college_name": college.name,
        "college_code": college.code,
        "plan": "free",
        "monthly_limit": 100,
        "admin_username": payload.admin_username,
    }


# ── [PHASE 8] Usage endpoint ─────────────────────────────────────────
@router.get("/usage", response_model=UsageResponse)
def get_my_usage(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    """
    [PHASE 8] Returns current user's usage stats.
    Students can see how many questions they've used this month.
    """
    from models import College
    from datetime import date

    college = db.query(College).filter_by(id=current_user.college_id).first()
    monthly_limit = college.monthly_limit if college else 100
    plan          = college.plan.value if college else "free"

    # Reset if new month
    current_month = date.today().strftime("%Y-%m")
    if current_user.last_reset_date != current_month:
        current_user.questions_this_month = 0
        current_user.last_reset_date = current_month
        db.commit()

    used      = current_user.questions_this_month
    remaining = max(0, monthly_limit - used)

    return {
        "username":       current_user.username,
        "plan":           plan,
        "monthly_limit":  monthly_limit,
        "used":           used,
        "remaining":      remaining,
        "reset_on":       f"1st of next month",
        "is_admin":       current_user.role.value in ("admin", "staff"),
    }

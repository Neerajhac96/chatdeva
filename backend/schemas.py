"""
schemas.py — Pydantic request/response models
----------------------------------------------
Separates API contracts from DB models.
Every route uses these for input validation and output serialisation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator
from models import UserRole, DocType


# ── Auth ──────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username:   str
    password:   str
    college_id: int
    role:       UserRole = UserRole.student

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Username cannot be empty.")
        return v.strip()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class UserResponse(BaseModel):
    id:         int
    username:   str
    role:       UserRole
    college_id: int
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── College ───────────────────────────────────────────────────────────
class CollegeResponse(BaseModel):
    id:         int
    name:       str
    code:       str
    created_at: datetime

    model_config = {"from_attributes": True}


class CollegeCreate(BaseModel):
    name: str
    code: str


# ── Documents ─────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id:            int
    filename:      str
    original_name: str
    doc_type:      DocType
    file_size_kb:  Optional[float]
    is_indexed:    bool
    uploader_id:   int
    college_id:    int
    created_at:    datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: int
    query:      str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty.")
        return v.strip()


class SourceMeta(BaseModel):
    filename:   str
    doc_type:   str
    uploaded_at: str


class ChatResponse(BaseModel):
    answer:     str
    sources:    List[SourceMeta]
    session_id: int


class SessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class SessionResponse(BaseModel):
    id:         int
    user_id:    int
    title:      str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id:         int
    session_id: int
    role:       str
    content:    str
    sources:    str       # JSON string — frontend parses this
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Admin ─────────────────────────────────────────────────────────────
class RoleUpdateRequest(BaseModel):
    user_id:  int
    new_role: UserRole


class AuditLogResponse(BaseModel):
    id:         int
    user_id:    Optional[int]
    action:     str
    detail:     Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── [PHASE 8] SaaS — College plan + usage schemas ─────────────────────
class CollegeRegisterRequest(BaseModel):
    """Public college self-registration request."""
    name:           str
    code:           str
    contact_email:  str
    admin_username: str
    admin_password: str

    @field_validator("admin_password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v):
        return v.strip().upper()


class CollegeDetailResponse(BaseModel):
    """Full college info including plan details."""
    id:            int
    name:          str
    code:          str
    plan:          str
    monthly_limit: int
    contact_email: Optional[str]
    is_active:     bool
    created_at:    datetime

    model_config = {"from_attributes": True}


class UsageResponse(BaseModel):
    """Student usage stats for the current month."""
    username:      str
    plan:          str
    monthly_limit: int
    used:          int
    remaining:     int
    reset_on:      str
    is_admin:      bool

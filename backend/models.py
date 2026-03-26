"""
models.py — Phase 8: SaaS models added
----------------------------------------
Changes from previous version:
  - College: added plan, monthly_limit, contact_email, is_active
  - User: added questions_this_month, last_reset_date
  - New: CollegePlan enum (free / pro)
  - All other models unchanged
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Enum, Boolean, Float,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ── Enums ─────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin   = "admin"
    staff   = "staff"
    student = "student"


class DocType(str, enum.Enum):
    notice    = "notice"
    syllabus  = "syllabus"
    timetable = "timetable"
    exam      = "exam"
    other     = "other"


class CollegePlan(str, enum.Enum):
    free = "free"   # 100 questions/student/month
    pro  = "pro"    # unlimited (future paid tier)


# ── Models ────────────────────────────────────────────────────────────
class College(Base):
    """
    [PHASE 8] Added:
      - plan          : free or pro
      - monthly_limit : max questions per student per month
      - contact_email : for SaaS onboarding
      - is_active     : can be disabled if unpaid
    """
    __tablename__ = "colleges"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    name           = Column(String(200), unique=True, nullable=False)
    code           = Column(String(50),  unique=True, nullable=False)
    # [PHASE 8] SaaS fields
    plan           = Column(Enum(CollegePlan), default=CollegePlan.free, nullable=False)
    monthly_limit  = Column(Integer, default=100)   # questions per student per month
    contact_email  = Column(String(200), nullable=True)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    users     = relationship("User",     back_populates="college")
    documents = relationship("Document", back_populates="college")


class User(Base):
    """
    [PHASE 8] Added:
      - questions_this_month : rolling counter, reset monthly
      - last_reset_date      : tracks when counter was last reset
    """
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(100), unique=True, nullable=False, index=True)
    email         = Column(String(200), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    college_id    = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    # [PHASE 8] Usage tracking
    questions_this_month = Column(Integer, default=0)
    last_reset_date      = Column(String(10), default="")  # YYYY-MM stored as string

    college       = relationship("College",     back_populates="users")
    documents     = relationship("Document",    back_populates="uploader")
    chat_sessions = relationship("ChatSession", back_populates="user",
                                 cascade="all, delete-orphan")
    audit_logs    = relationship("AuditLog",    back_populates="user")


class Document(Base):
    __tablename__ = "documents"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    filename      = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    doc_type      = Column(Enum(DocType), default=DocType.other, nullable=False)
    file_size_kb  = Column(Float,   nullable=True)
    is_indexed    = Column(Boolean, default=False)
    uploader_id   = Column(Integer, ForeignKey("users.id"),    nullable=False)
    college_id    = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User",    back_populates="documents")
    college  = relationship("College", back_populates="documents")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    title      = Column(String(200), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    user     = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session",
                            cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    sources    = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    action     = Column(String(100), nullable=False)
    detail     = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")

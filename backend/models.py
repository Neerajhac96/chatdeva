"""
models.py — SQLAlchemy ORM models
-----------------------------------
All database tables defined here.
Relationships are explicit so queries are clean and type-safe.

Tables:
  users         — accounts with role + college isolation
  colleges      — college registry (optional expansion)
  documents     — uploaded file metadata per college
  chat_sessions — named conversation threads per user
  chat_messages — individual messages within a session
  audit_logs    — optional security audit trail
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


# ── Models ────────────────────────────────────────────────────────────
class College(Base):
    """
    Colleges registry.
    Every user, document, and chat message is scoped to a college_id.
    Adding a new college = inserting one row here.
    """
    __tablename__ = "colleges"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(200), unique=True, nullable=False)
    code       = Column(String(50),  unique=True, nullable=False)  # e.g. "ABESEC"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users     = relationship("User",     back_populates="college")
    documents = relationship("Document", back_populates="college")


class User(Base):
    """
    User account.
    college_id enforces data isolation — users only see their college's data.
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

    # Relationships
    college       = relationship("College",     back_populates="users")
    documents     = relationship("Document",    back_populates="uploader")
    chat_sessions = relationship("ChatSession", back_populates="user",
                                 cascade="all, delete-orphan")
    audit_logs    = relationship("AuditLog",    back_populates="user")


class Document(Base):
    """
    Uploaded document metadata.
    Physical file lives at: uploads/{college_id}/{filename}
    Vector chunks live in:  vector_store/{college_id}/
    """
    __tablename__ = "documents"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    filename      = Column(String(255), nullable=False)        # stored filename (unique)
    original_name = Column(String(255), nullable=False)        # original upload name
    doc_type      = Column(Enum(DocType), default=DocType.other, nullable=False)
    file_size_kb  = Column(Float,   nullable=True)
    is_indexed    = Column(Boolean, default=False)             # True after RAG processing
    uploader_id   = Column(Integer, ForeignKey("users.id"),    nullable=False)
    college_id    = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Relationships
    uploader = relationship("User",    back_populates="documents")
    college  = relationship("College", back_populates="documents")


class ChatSession(Base):
    """
    A named conversation thread belonging to one user.
    One user can have many sessions (New Chat = new session).
    """
    __tablename__ = "chat_sessions"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    title      = Column(String(200), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user     = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session",
                            cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """
    A single message within a chat session.
    sources stores JSON-serialised list of source metadata.
    """
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role       = Column(String(20), nullable=False)   # "user" | "assistant"
    content    = Column(Text, nullable=False)
    sources    = Column(Text, default="[]")            # JSON list of source dicts
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class AuditLog(Base):
    """
    Optional security audit trail.
    Logs sensitive actions: login, upload, delete, role change.
    """
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    action     = Column(String(100), nullable=False)   # e.g. "document.upload"
    detail     = Column(Text, nullable=True)           # JSON extra context
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

"""
database.py — SQLAlchemy engine + session management
------------------------------------------------------
Provides:
  - engine        : SQLAlchemy engine (SQLite dev / Postgres prod)
  - get_db()      : FastAPI dependency that yields a DB session
  - init_db()     : creates all tables + seeds a default college on startup
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))


import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config import settings
from models import Base, College, User, UserRole
import bcrypt

logger = logging.getLogger(__name__)

# ── Engine ────────────────────────────────────────────────────────────
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,           # Set True to log raw SQL during debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── FastAPI dependency ────────────────────────────────────────────────
def get_db():
    """
    Yields a SQLAlchemy session and guarantees it is closed after the request.
    Use as a FastAPI dependency: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Initialisation ────────────────────────────────────────────────────
def init_db():
    """
    Creates all tables and seeds default data if the DB is empty.
    Called once at FastAPI startup.
    """
    logger.info("Initialising database...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_default_data(db)
    finally:
        db.close()

    logger.info("✅ Database ready.")


def _seed_default_data(db: Session):
    """
    Seeds one default college and one default admin account
    so the system is usable immediately after first run.
    Skip if data already exists.
    """
    # Default college
    college = db.query(College).filter_by(code="DEFAULT").first()
    if not college:
        college = College(name="Default College", code="DEFAULT")
        db.add(college)
        db.commit()
        db.refresh(college)
        logger.info(f"✅ Seeded default college: id={college.id}")

    # Default admin
    admin = db.query(User).filter_by(username="admin").first()
    if not admin:
        password_hash = bcrypt.hashpw(
            b"admin123", bcrypt.gensalt(rounds=12)
        ).decode("utf-8")
        admin = User(
            username="admin",
            password_hash=password_hash,
            role=UserRole.admin,
            college_id=college.id,
        )
        db.add(admin)
        db.commit()
        logger.info("✅ Seeded default admin (username=admin, password=admin123)")
        logger.warning("⚠️  CHANGE THE DEFAULT ADMIN PASSWORD before going to production!")

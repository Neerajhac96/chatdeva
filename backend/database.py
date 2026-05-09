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
from models import Base, College, User, UserRole, CollegeInvite
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
def _run_migrations():
    """
    Adds new columns to existing tables safely.
    Uses IF NOT EXISTS (Postgres) or try/except (SQLite).
    Safe to run on every startup — skips already-existing columns.
    """
    from sqlalchemy import text
    is_postgres = "postgresql" in settings.DATABASE_URL

    if is_postgres:
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS questions_this_month INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reset_date VARCHAR(10) DEFAULT ''",
            "ALTER TABLE colleges ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free'",
            "ALTER TABLE colleges ADD COLUMN IF NOT EXISTS monthly_limit INTEGER DEFAULT 100",
            "ALTER TABLE colleges ADD COLUMN IF NOT EXISTS contact_email VARCHAR(200)",
            "ALTER TABLE colleges ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        ]
    else:
        migrations = [
            "ALTER TABLE users ADD COLUMN questions_this_month INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_reset_date VARCHAR(10) DEFAULT ''",
            "ALTER TABLE colleges ADD COLUMN plan VARCHAR(20) DEFAULT 'free'",
            "ALTER TABLE colleges ADD COLUMN monthly_limit INTEGER DEFAULT 100",
            "ALTER TABLE colleges ADD COLUMN contact_email VARCHAR(200)",
            "ALTER TABLE colleges ADD COLUMN is_active BOOLEAN DEFAULT 1",
        ]

    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    logger.warning(f"Migration skipped: {e}")


def init_db():
    """
    Creates all tables, runs migrations, and seeds default data.
    Called once at FastAPI startup. Safe to run repeatedly.
    """
    logger.info("Initialising database...")
    Base.metadata.create_all(bind=engine)
    _run_migrations()

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

    # Default admin for the default college
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

    # [SECURITY] Super admin — controls system-wide invites
    # Username from env var, defaults to "superadmin"
    import os
    super_username = os.getenv("SUPER_ADMIN_USERNAME", "superadmin")
    super_password = os.getenv("SUPER_ADMIN_PASSWORD", "superadmin123")
    super_admin = db.query(User).filter_by(username=super_username).first()
    if not super_admin:
        super_hash = bcrypt.hashpw(
            super_password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")
        super_admin = User(
            username=super_username,
            password_hash=super_hash,
            role=UserRole.super_admin,
            college_id=college.id,
        )
        db.add(super_admin)
        db.commit()
        logger.info(f"✅ Seeded super admin (username={super_username})")
        logger.warning("⚠️  SET SUPER_ADMIN_USERNAME and SUPER_ADMIN_PASSWORD env vars in production!")

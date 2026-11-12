"""
SQLAlchemy Database setup and session management.
Supports SQLite out of the box and PostgreSQL in production.
"""
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

def utcnow():
    """Returns timezone-naive UTC datetime for clean DB compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# For SQLite, enable check_same_thread=False
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency for yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

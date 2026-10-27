"""
AICTE FlowOps — Database Engine & Session Management

Provides:
- ``engine``  — the SQLAlchemy async-compatible engine bound to DATABASE_URL.
- ``SessionLocal`` — a session factory for request-scoped DB sessions.
- ``Base`` — declarative base for all ORM models.
- ``get_db()`` — FastAPI dependency that yields a session and auto-closes it.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from typing import Generator

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Shared declarative base — every model inherits from this."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session, closes on teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

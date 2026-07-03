"""Database engine, session management, and declarative base.

All module models inherit from Base. Modules must not query each other's
tables directly — cross-module access goes through each module's service
layer (see BRD §7.3).
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    kwargs = {}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Create all tables. Development convenience; production uses Alembic."""
    # Import all module models so they register on Base.metadata.
    from app.modules import models_registry  # noqa: F401

    Base.metadata.create_all(bind=engine)

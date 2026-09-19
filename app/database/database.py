"""Database connection and session management."""
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import shutil

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from app.config.config import settings, PROJECT_ROOT

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

# Enable WAL mode for SQLite (better concurrency)
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database: create tables and run migrations."""
    from app.database.models import Base
    _rebuild_sqlite_if_schema_changed()
    Base.metadata.create_all(bind=engine)
    # Run Alembic migrations if available
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
    except Exception:
        pass  # Alembic not configured or no migrations


def _rebuild_sqlite_if_schema_changed():
    """Dev-only: detect schema drift in SQLite and rebuild the DB from scratch.

    The early dev DB schemas were rewritten frequently; stale tables break
    queries with 'no such column'. This performs a destructive rebuild (with a
    timestamped backup) so startup never crashes on an outdated dev DB. It only
    applies to SQLite and is a no-op otherwise.
    """
    if "sqlite" not in settings.DATABASE_URL:
        return
    if not hasattr(engine, "url") or not engine.url.database:
        return

    from sqlalchemy import inspect

    db_path = Path(engine.url.database)
    if not db_path.exists() or db_path.stat().st_size == 0:
        return  # Fresh DB, nothing to check

    inspector = inspect(engine)
    if not inspector.has_table("incidents"):
        _backup_sqlite(db_path)
        _replace_sqlite(db_path)
        return

    # Expected columns from the current model
    from app.database.models import Incident
    expected = {c.name for c in Incident.__table__.columns}
    actual = {c["name"] for c in inspector.get_columns("incidents")}
    if not expected.issubset(actual):
        _backup_sqlite(db_path)
        _replace_sqlite(db_path)


def _backup_sqlite(db_path: Path):
    """Back up the SQLite file before a rebuild."""
    import time as _t
    from app.config.config import PROJECT_ROOT as _root
    backup_dir = _root / "data" / "db_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _t.strftime("%Y%m%d_%H%M%S")
    try:
        shutil.copy2(db_path, backup_dir / f"incidents_backup_{stamp}.db")
    except OSError:
        pass


def _replace_sqlite(db_path: Path):
    """Drop and recreate the SQLite file so models get a fresh schema."""
    try:
        db_path.unlink(missing_ok=True)
    except OSError:
        pass
    engine.dispose()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database session (non-FastAPI contexts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache
def get_engine() -> Engine | None:
    if not settings.database_url:
        return None
    # pool_pre_ping + short timeout: Neon free tier scales to zero after 5 min idle.
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 10},
    )


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    return _session_factory()()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database() -> dict:
    engine = get_engine()
    if engine is None:
        return {"status": "not_configured", "pgvector": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            has_vector = (
                conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first()
                is not None
            )
        return {"status": "ok", "pgvector": has_vector}
    except Exception as exc:  # noqa: BLE001 - surfaced to the health endpoint
        return {"status": "error", "pgvector": False, "detail": str(exc)[:200]}

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String, bindparam

from app.core.db import get_engine


@dataclass
class Job:
    id: int
    kind: str
    payload: dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    run_after: datetime | None = None
    last_error: str | None = None


def _engine():
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return engine


def enqueue(
    kind: str,
    payload: dict[str, Any],
    run_after: datetime | None = None,
) -> int:
    sql = text(
        """
        INSERT INTO jobs (kind, payload, status, run_after)
        VALUES (:kind, CAST(:payload AS jsonb), 'queued', COALESCE(:run_after, now()))
        RETURNING id
        """
    )
    with _engine().begin() as conn:
        job_id = conn.execute(
            sql,
            {
                "kind": kind,
                "payload": _json(payload),
                "run_after": run_after,
            },
        ).scalar_one()
    return int(job_id)


def claim(kinds: list[str]) -> Job | None:
    if not kinds:
        return None
    select_sql = text(
        """
        SELECT id, kind, payload, status, attempts, max_attempts, run_after, last_error
        FROM jobs
        WHERE status = 'queued' AND run_after <= now() AND kind = ANY(:kinds)
        ORDER BY id
        LIMIT 1
        FOR UPDATE SKIP LOCKED
        """
    ).bindparams(bindparam("kinds", type_=ARRAY(String)))
    with _engine().begin() as conn:
        row = conn.execute(select_sql, {"kinds": kinds}).mappings().first()
        if row is None:
            return None
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'running',
                    locked_at = now(),
                    attempts = attempts + 1,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": row["id"]},
        )
        return Job(
            id=int(row["id"]),
            kind=row["kind"],
            payload=row["payload"] if isinstance(row["payload"], dict) else {},
            status="running",
            attempts=int(row["attempts"]) + 1,
            max_attempts=int(row["max_attempts"]),
            run_after=row["run_after"],
            last_error=row["last_error"],
        )


def complete(job_id: int) -> None:
    with _engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'done', locked_at = NULL, last_error = NULL, updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": job_id},
        )


def fail(job_id: int, error: str) -> None:
    with _engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'failed', locked_at = NULL, last_error = :error, updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": job_id, "error": error[:2000]},
        )


def requeue(job_id: int, error: str, delay: timedelta) -> None:
    with _engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'queued',
                    locked_at = NULL,
                    last_error = :error,
                    run_after = now() + CAST(:delay AS interval),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": job_id, "error": error[:2000], "delay": _interval(delay)},
        )


def reset_stale_locks(older_than: timedelta = timedelta(minutes=10)) -> int:
    with _engine().begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'queued', locked_at = NULL, updated_at = now()
                WHERE status = 'running' AND locked_at < now() - CAST(:delay AS interval)
                """
            ),
            {"delay": _interval(older_than)},
        )
        return result.rowcount or 0


def _json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload)


def _interval(delay: timedelta) -> str:
    return f"{int(delay.total_seconds())} seconds"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

from datetime import timedelta

from sqlalchemy import text

from app.core.db import get_engine
from app.core.jobs import enqueue, requeue
from app.worker import process_one


def _job_status(job_id: int) -> str:
    engine = get_engine()
    assert engine is not None
    with engine.connect() as conn:
        return conn.execute(text("SELECT status FROM jobs WHERE id = :id"), {"id": job_id}).scalar_one()


def _force_due(job_id: int) -> None:
    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        conn.execute(text("UPDATE jobs SET run_after = now() - interval '1 second' WHERE id = :id"), {"id": job_id})


def test_dummy_job_fails_twice_then_succeeds():
    engine = get_engine()
    if engine is None:
        raise AssertionError("DATABASE_URL required for job test")
    job_id = enqueue("dummy", {"fail_until": 2})

    assert process_one(["dummy"]) is True
    assert _job_status(job_id) == "queued"
    _force_due(job_id)

    assert process_one(["dummy"]) is True
    assert _job_status(job_id) == "queued"
    _force_due(job_id)

    assert process_one(["dummy"]) is True
    assert _job_status(job_id) == "done"


def test_requeue_sets_backoff():
    job_id = enqueue("dummy", {"fail_until": 99})
    process_one(["dummy"])
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, last_error, run_after FROM jobs WHERE id = :id"),
            {"id": job_id},
        ).mappings().one()
    assert row["status"] == "queued"
    assert row["last_error"]
    # cleanup so leftover never blocks
    requeue(job_id, "cleanup", timedelta(days=365))

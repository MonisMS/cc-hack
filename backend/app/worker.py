"""Job worker: `uv run python -m app.worker` from backend/."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from app.core.errors import PermanentError, RetryableError
from app.core.jobs import Job, claim, complete, fail, requeue, reset_stale_locks

log = logging.getLogger("fieldproof.worker")

Handler = Callable[[dict[str, Any]], None]
HANDLERS: dict[str, Handler] = {}


def handler(kind: str):
    def deco(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn

    return deco


@handler("dummy")
def handle_dummy(payload: dict[str, Any]) -> None:
    fail_until = int(payload.get("fail_until", 0))
    attempt = int(payload.get("_attempt", 0))
    if attempt <= fail_until:
        raise RetryableError(f"dummy forced failure on attempt {attempt}")
    log.info("dummy job ok on attempt %s payload=%s", attempt, payload)


def register_analyze_handler() -> None:
    if "analyze_asset" in HANDLERS:
        return
    from app.fieldproof.pipelines import analyze_asset

    HANDLERS["analyze_asset"] = analyze_asset


def process_one(kinds: list[str] | None = None) -> bool:
    if kinds is None:
        register_analyze_handler()
    kinds = kinds or list(HANDLERS)
    job = claim(kinds)
    if job is None:
        return False
    payload = dict(job.payload)
    payload["_attempt"] = job.attempts
    fn = HANDLERS.get(job.kind)
    try:
        if fn is None:
            raise PermanentError(f"unknown job kind {job.kind}")
        fn(payload)
        complete(job.id)
        log.info("job %s %s done", job.id, job.kind)
    except RetryableError as exc:
        _retry_or_fail(job, str(exc))
    except PermanentError as exc:
        fail(job.id, str(exc))
        log.warning("job %s %s permanent fail: %s", job.id, job.kind, exc)
    except Exception as exc:  # noqa: BLE001
        _retry_or_fail(job, f"{type(exc).__name__}: {exc}")
        log.exception("job %s %s crashed", job.id, job.kind)
    return True


def _retry_or_fail(job: Job, error: str) -> None:
    if job.attempts < job.max_attempts:
        delay = timedelta(seconds=10 * (2 ** job.attempts))
        requeue(job.id, error, delay)
        log.warning("job %s retry in %ss: %s", job.id, delay.total_seconds(), error)
    else:
        fail(job.id, error)
        log.warning("job %s exhausted retries: %s", job.id, error)


def run_forever(poll_s: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    register_analyze_handler()
    n = reset_stale_locks()
    log.info("worker start; reset %s stale locks; kinds=%s", n, sorted(HANDLERS))
    while True:
        if not process_one():
            time.sleep(poll_s)


if __name__ == "__main__":
    run_forever()

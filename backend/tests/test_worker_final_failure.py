from app.core.errors import PermanentError
from app.core.jobs import enqueue
from app.worker import FINAL_FAILURE_HOOKS, HANDLERS, process_one


def test_final_failure_hook_called_once_on_permanent_error():
    calls: list[tuple[dict, str]] = []

    def always_fails(payload: dict) -> None:
        raise PermanentError("boom")

    def hook(payload: dict, error: str) -> None:
        calls.append((payload, error))

    HANDLERS["test_final_failure"] = always_fails
    FINAL_FAILURE_HOOKS["test_final_failure"] = hook
    try:
        job_id = enqueue("test_final_failure", {"x": 1})
        assert process_one(["test_final_failure"]) is True
        assert len(calls) == 1
        assert calls[0][1] == "boom"
        assert calls[0][0]["x"] == 1
        assert job_id
    finally:
        HANDLERS.pop("test_final_failure", None)
        FINAL_FAILURE_HOOKS.pop("test_final_failure", None)

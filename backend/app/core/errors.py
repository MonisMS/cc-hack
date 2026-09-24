class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


class RetryableError(Exception):
    """Transient failure: worker requeues with backoff."""


class PermanentError(Exception):
    """Do not retry; mark the job (and usually the entity) failed."""

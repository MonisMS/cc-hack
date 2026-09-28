from __future__ import annotations

import logging
import os
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils

from app.core.config import settings
from app.core.errors import PermanentError, RetryableError
from app.fieldproof.transforms import NamedTransform, chain

log = logging.getLogger("fieldproof.cloudinary_gw")

_configured = False

ADMIN_BUDGET_WARN = 200
ADMIN_BUDGET_LIMIT = 300
_admin_calls: deque[datetime] = deque()


def _configure() -> None:
    global _configured
    if _configured:
        return
    if not settings.cloudinary_url:
        raise PermanentError("CLOUDINARY_URL is not configured")
    os.environ["CLOUDINARY_URL"] = settings.cloudinary_url
    cloudinary.reset_config()
    cloudinary.config(secure=True)
    _configured = True


def _admin_call(name: str, fn: Callable[..., Any], *a: Any, **kw: Any) -> Any:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)
    while _admin_calls and _admin_calls[0] < cutoff:
        _admin_calls.popleft()
    if len(_admin_calls) >= ADMIN_BUDGET_LIMIT:
        raise RetryableError("admin api budget")
    if len(_admin_calls) >= ADMIN_BUDGET_WARN:
        log.warning("cloudinary admin call budget at %s/%s", len(_admin_calls), ADMIN_BUDGET_LIMIT)
    _admin_calls.append(now)
    log.info("cloudinary admin call: %s", name)
    try:
        return fn(*a, **kw)
    except Exception as exc:
        _map_cld_error(exc)
        raise


def get_resource(public_id: str, resource_type: str = "image", **kw: Any) -> dict:
    _configure()
    return _admin_call(
        "resource",
        cloudinary.api.resource,
        public_id,
        resource_type=resource_type,
        media_metadata=True,
        **kw,
    )


def url(
    public_id: str,
    preset: NamedTransform,
    resource_type: str = "image",
    **kw: Any,
) -> str:
    if settings.cloudinary_url:
        _configure()
    else:
        cloudinary.config(cloud_name="demo", secure=True)
    transformation = chain(preset, **kw)
    result, _ = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type=resource_type,
        secure=True,
        transformation=transformation,
        format=kw.get("format"),
    )
    return result


def raw_url(public_id: str, transformation: list[dict]) -> str:
    if settings.cloudinary_url:
        _configure()
    else:
        cloudinary.config(cloud_name="demo", secure=True)
    result, _ = cloudinary.utils.cloudinary_url(public_id, secure=True, transformation=transformation)
    return result


def upload_derived(data: bytes, folder: str, **kw: Any) -> dict:
    _configure()
    try:
        return cloudinary.uploader.upload(
            data,
            folder=folder,
            resource_type=kw.get("resource_type", "image"),
            **{k: v for k, v in kw.items() if k != "resource_type"},
        )
    except Exception as exc:
        _map_cld_error(exc)
        raise


def usage() -> dict:
    _configure()
    return _admin_call("usage", cloudinary.api.usage)


USAGE_CACHE_SECONDS = 600
_usage_cache: dict[str, Any] | None = None
_usage_cache_at: datetime | None = None


def cached_usage() -> dict | None:
    """usage() cached for USAGE_CACHE_SECONDS. Fails open: returns the last known value
    (or None) if a fresh call isn't due or the call itself fails."""
    global _usage_cache, _usage_cache_at
    now = datetime.now(timezone.utc)
    if _usage_cache_at is not None and (now - _usage_cache_at).total_seconds() < USAGE_CACHE_SECONDS:
        return _usage_cache
    try:
        resp = usage()
    except Exception:
        log.warning("cloudinary usage() failed; credit guard fails open", exc_info=True)
        return _usage_cache
    _usage_cache = resp
    _usage_cache_at = now
    return resp


def _map_cld_error(exc: Exception) -> None:
    msg = str(exc)
    status = getattr(exc, "http_code", None) or getattr(exc, "code", None)
    if status in {404, 400} or "not found" in msg.lower():
        raise PermanentError(msg) from exc
    if status in {420, 429} or (isinstance(status, int) and status >= 500):
        raise RetryableError(msg) from exc
    raise RetryableError(msg) from exc

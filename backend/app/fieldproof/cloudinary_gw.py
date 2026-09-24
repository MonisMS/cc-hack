from __future__ import annotations

from typing import Any

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils

from app.core.config import settings
from app.core.errors import PermanentError, RetryableError
from app.fieldproof.transforms import NamedTransform, chain

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    if not settings.cloudinary_url:
        raise PermanentError("CLOUDINARY_URL is not configured")
    cloudinary.config(cloudinary_url=settings.cloudinary_url, secure=True)
    _configured = True


def get_resource(public_id: str, resource_type: str = "image", **kw: Any) -> dict:
    _configure()
    try:
        return cloudinary.api.resource(
            public_id,
            resource_type=resource_type,
            media_metadata=True,
            **kw,
        )
    except Exception as exc:
        _map_cld_error(exc)
        raise


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
    try:
        return cloudinary.api.usage()
    except Exception as exc:
        _map_cld_error(exc)
        raise


def _map_cld_error(exc: Exception) -> None:
    msg = str(exc)
    status = getattr(exc, "http_code", None) or getattr(exc, "code", None)
    if status in {404, 400} or "not found" in msg.lower():
        raise PermanentError(msg) from exc
    if status in {420, 429} or (isinstance(status, int) and status >= 500):
        raise RetryableError(msg) from exc
    raise RetryableError(msg) from exc

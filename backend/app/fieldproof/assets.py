"""Asset registration. A plain function so the seed script can call it without HTTP."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.db import get_engine
from app.core.errors import ApiError
from app.core.jobs import enqueue


def register_asset(
    project_id: UUID,
    cld_public_id: str,
    cld_asset_id: str,
    cld_version: int,
    secure_url: str,
    resource_type: str = "image",
    format: str | None = None,
    width: int | None = None,
    height: int | None = None,
    bytes: int | None = None,
    duration_s: float | None = None,
    device_lat: float | None = None,
    device_lng: float | None = None,
    consent_confirmed: bool = False,
    image_metadata: dict[str, Any] | None = None,
    detection: dict[str, Any] | None = None,
) -> dict:
    """Idempotent on cld_public_id. Returns {asset_id, status, job_id}. job_id is None on conflict."""
    engine = get_engine()
    if engine is None:
        raise ApiError("INTERNAL", "database not configured", 500)

    asset_id = uuid4()
    with engine.begin() as conn:
        if not conn.execute(
            text("SELECT 1 FROM projects WHERE id = :id"), {"id": str(project_id)}
        ).first():
            raise ApiError("NOT_FOUND", f"project {project_id} not found", 404)

        inserted = conn.execute(
            text(
                """
                INSERT INTO assets (
                    id, project_id, cld_public_id, cld_asset_id, cld_version, resource_type,
                    format, width, height, bytes, duration_s, secure_url, consent_confirmed,
                    status, media_metadata, cld_detection
                ) VALUES (
                    :id, :project_id, :cld_public_id, :cld_asset_id, :cld_version, :resource_type,
                    :format, :width, :height, :bytes, :duration_s, :secure_url, :consent_confirmed,
                    'pending', CAST(:media_metadata AS jsonb), CAST(:cld_detection AS jsonb)
                )
                ON CONFLICT (cld_public_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": str(asset_id),
                "project_id": str(project_id),
                "cld_public_id": cld_public_id,
                "cld_asset_id": cld_asset_id,
                "cld_version": cld_version,
                "resource_type": resource_type,
                "format": format,
                "width": width,
                "height": height,
                "bytes": bytes,
                "duration_s": duration_s,
                "secure_url": secure_url,
                "consent_confirmed": consent_confirmed,
                "media_metadata": _json(image_metadata or {}),
                "cld_detection": _json(detection or {}),
            },
        ).mappings().first()

        if inserted is None:
            existing = conn.execute(
                text("SELECT id, status FROM assets WHERE cld_public_id = :pid"),
                {"pid": cld_public_id},
            ).mappings().first()
            return {"asset_id": str(existing["id"]), "status": existing["status"], "job_id": None}

    job_id = enqueue(
        "analyze_asset",
        {"asset_id": str(asset_id), "device_lat": device_lat, "device_lng": device_lng},
    )
    return {"asset_id": str(asset_id), "status": "pending", "job_id": job_id}


def _json(obj: Any) -> str:
    import json

    return json.dumps(obj)

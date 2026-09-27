from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.db import get_engine
from app.core.errors import ApiError
from app.core.jobs import enqueue
from app.fieldproof import assets as assets_module
from app.fieldproof import search as search_module
from app.fieldproof import sites, urls
from app.fieldproof.schemas import (
    AssetPatch,
    AssetRegister,
    ProjectCreate,
    SearchRequest,
    SiteCreate,
    SitePatch,
)

router = APIRouter(prefix="/api")


def _engine():
    engine = get_engine()
    if engine is None:
        raise ApiError("INTERNAL", "database not configured", 500)
    return engine


_PROJECT_SELECT = """
    SELECT p.id, p.name, p.description, p.started_on, p.created_at,
           COUNT(a.id) AS asset_count,
           COUNT(a.id) FILTER (WHERE a.status = 'ready') AS ready_count,
           COUNT(a.id) FILTER (WHERE a.status = 'failed') AS failed_count,
           (SELECT COUNT(*) FROM sites s WHERE s.project_id = p.id) AS site_count
    FROM projects p
    LEFT JOIN assets a ON a.project_id = p.id
"""

_SITE_SELECT = """
    SELECT s.id, s.project_id, s.name, s.lat, s.lng, s.radius_m,
           COUNT(a.id) AS asset_count
    FROM sites s
    LEFT JOIN assets a ON a.site_id = s.id
"""


def _project_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "started_on": row["started_on"].isoformat() if row["started_on"] else None,
        "created_at": row["created_at"],
        "asset_count": row["asset_count"],
        "ready_count": row["ready_count"],
        "failed_count": row["failed_count"],
        "site_count": row["site_count"],
    }


def _site_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "project_id": str(row["project_id"]),
        "name": row["name"],
        "lat": row["lat"],
        "lng": row["lng"],
        "radius_m": row["radius_m"],
        "asset_count": row["asset_count"],
    }


def _get_project_row(conn, project_id: UUID):
    row = conn.execute(
        text(f"{_PROJECT_SELECT} WHERE p.id = :id GROUP BY p.id"),
        {"id": str(project_id)},
    ).mappings().first()
    if row is None:
        raise ApiError("NOT_FOUND", f"project {project_id} not found", 404)
    return row


def _project_exists(conn, project_id: UUID) -> bool:
    return (
        conn.execute(
            text("SELECT 1 FROM projects WHERE id = :id"), {"id": str(project_id)}
        ).first()
        is not None
    )


@router.get("/projects")
def list_projects() -> dict:
    with _engine().connect() as conn:
        rows = conn.execute(
            text(f"{_PROJECT_SELECT} GROUP BY p.id ORDER BY p.created_at DESC")
        ).mappings().all()
    return {"items": [_project_dict(r) for r in rows]}


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate) -> dict:
    project_id = uuid4()
    with _engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO projects (id, name, description, started_on)
                VALUES (:id, :name, :description, :started_on)
                """
            ),
            {
                "id": str(project_id),
                "name": body.name,
                "description": body.description,
                "started_on": body.started_on,
            },
        )
        row = _get_project_row(conn, project_id)
    return _project_dict(row)


@router.get("/projects/{project_id}")
def get_project(project_id: UUID) -> dict:
    with _engine().connect() as conn:
        row = _get_project_row(conn, project_id)
    return _project_dict(row)


@router.get("/projects/{project_id}/sites")
def list_sites(project_id: UUID) -> dict:
    with _engine().connect() as conn:
        _get_project_row(conn, project_id)
        rows = conn.execute(
            text(f"{_SITE_SELECT} WHERE s.project_id = :project_id GROUP BY s.id ORDER BY s.created_at"),
            {"project_id": str(project_id)},
        ).mappings().all()
    return {"items": [_site_dict(r) for r in rows]}


@router.post("/projects/{project_id}/sites", status_code=201)
def create_site(project_id: UUID, body: SiteCreate) -> dict:
    site_id = uuid4()
    with _engine().begin() as conn:
        if not _project_exists(conn, project_id):
            raise ApiError("NOT_FOUND", f"project {project_id} not found", 404)
        conn.execute(
            text(
                """
                INSERT INTO sites (id, project_id, name, lat, lng, radius_m)
                VALUES (:id, :project_id, :name, :lat, :lng, :radius_m)
                """
            ),
            {
                "id": str(site_id),
                "project_id": str(project_id),
                "name": body.name,
                "lat": body.lat,
                "lng": body.lng,
                "radius_m": body.radius_m,
            },
        )
        row = conn.execute(
            text(f"{_SITE_SELECT} WHERE s.id = :id GROUP BY s.id"),
            {"id": str(site_id)},
        ).mappings().first()
    return _site_dict(row)


@router.patch("/sites/{site_id}")
def patch_site(site_id: UUID, body: SitePatch) -> dict:
    fields = body.model_dump(exclude_unset=True)
    with _engine().begin() as conn:
        existing = conn.execute(
            text(f"{_SITE_SELECT} WHERE s.id = :id GROUP BY s.id"),
            {"id": str(site_id)},
        ).mappings().first()
        if existing is None:
            raise ApiError("NOT_FOUND", f"site {site_id} not found", 404)
        if fields:
            set_clauses = [f"{k} = :{k}" for k in fields]
            conn.execute(
                text(f"UPDATE sites SET {', '.join(set_clauses)} WHERE id = :id"),
                {**fields, "id": str(site_id)},
            )
        row = conn.execute(
            text(f"{_SITE_SELECT} WHERE s.id = :id GROUP BY s.id"),
            {"id": str(site_id)},
        ).mappings().first()
    return _site_dict(row)


# ---- assets -----------------------------------------------------------------

_ASSET_SELECT = """
    SELECT a.id, a.project_id, a.site_id, sit.name AS site_name, a.status, a.resource_type,
           a.cld_public_id, a.cld_version, a.secure_url, a.width, a.height,
           a.captured_at, a.captured_at_source, a.lat, a.lng, a.location_source,
           a.consent_confirmed, a.error, a.created_at
    FROM assets a
    LEFT JOIN sites sit ON sit.id = a.site_id
"""

_TAG_ORDER_SQL = """
    ORDER BY
        CASE source WHEN 'clip' THEN 0 WHEN 'cld_detection' THEN 1 ELSE 2 END,
        CASE WHEN source = 'clip' THEN rank END ASC NULLS LAST,
        CASE WHEN source = 'cld_detection' THEN score END DESC NULLS LAST
"""


def _get_asset_row(conn, asset_id: UUID):
    row = conn.execute(
        text(f"{_ASSET_SELECT} WHERE a.id = :id"), {"id": str(asset_id)}
    ).mappings().first()
    if row is None:
        raise ApiError("NOT_FOUND", f"asset {asset_id} not found", 404)
    return row


def _bulk_tags(conn, asset_ids: list[UUID]) -> dict:
    if not asset_ids:
        return {}
    rows = conn.execute(
        text(
            f"""
            SELECT asset_id, tag, source, score, rank
            FROM asset_tags
            WHERE asset_id = ANY(CAST(:ids AS uuid[]))
            {_TAG_ORDER_SQL}
            """
        ).bindparams(bindparam("ids", type_=ARRAY(String))),
        {"ids": [str(i) for i in asset_ids]},
    ).mappings().all()
    by_asset: dict[str, list[dict]] = {}
    for r in rows:
        by_asset.setdefault(str(r["asset_id"]), []).append(
            {"tag": r["tag"], "source": r["source"], "score": r["score"], "rank": r["rank"]}
        )
    return by_asset


def _asset_tags(conn, asset_id: UUID) -> list[dict]:
    return _bulk_tags(conn, [asset_id]).get(str(asset_id), [])


def _round3(v: float | None) -> float | None:
    return round(v, 3) if v is not None else None


def _asset_card(row, tags: list[dict]) -> dict:
    return {
        "id": str(row["id"]),
        "project_id": str(row["project_id"]),
        "site_id": str(row["site_id"]) if row["site_id"] else None,
        "site_name": row["site_name"],
        "status": row["status"],
        "resource_type": row["resource_type"],
        "thumb_url": urls.thumb_url(row),
        "captured_at": row["captured_at"],
        "tags": tags,
    }


def _asset_detail(row, tags: list[dict]) -> dict:
    return {
        **_asset_card(row, tags),
        "cld_public_id": row["cld_public_id"],
        "cld_version": row["cld_version"],
        "secure_url": row["secure_url"],
        "compare_url": urls.compare_url(row),
        "width": row["width"],
        "height": row["height"],
        "captured_at_source": row["captured_at_source"],
        "lat_r": _round3(row["lat"]),
        "lng_r": _round3(row["lng"]),
        "location_source": row["location_source"],
        "consent_confirmed": row["consent_confirmed"],
        "error": row["error"],
    }


def _encode_cursor(created_at: datetime, asset_id: Any) -> str:
    raw = f"{created_at.isoformat()}|{asset_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        iso, cid = raw.split("|", 1)
        return datetime.fromisoformat(iso), cid
    except Exception as exc:
        raise ApiError("VALIDATION_ERROR", "invalid cursor", 422) from exc


@router.post("/assets/register")
def register_asset(body: AssetRegister) -> JSONResponse:
    result = assets_module.register_asset(**body.model_dump())
    status_code = 200 if result["job_id"] is None else 202
    return JSONResponse(status_code=status_code, content=result)


@router.get("/assets")
def list_assets(
    project_id: UUID,
    site_id: UUID | None = None,
    tag: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=30, ge=1, le=60),
) -> dict:
    where = ["a.project_id = :project_id"]
    params: dict[str, Any] = {"project_id": str(project_id), "limit": limit}
    if site_id is not None:
        where.append("a.site_id = :site_id")
        params["site_id"] = str(site_id)
    if status is not None:
        where.append("a.status = :status")
        params["status"] = status
    if tag is not None:
        where.append("EXISTS (SELECT 1 FROM asset_tags t WHERE t.asset_id = a.id AND t.tag = :tag)")
        params["tag"] = tag
    if cursor is not None:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        where.append("(a.created_at, a.id) < (:cursor_created_at, :cursor_id)")
        params["cursor_created_at"] = cursor_created_at
        params["cursor_id"] = cursor_id

    sql = f"""
        SELECT a.id, a.project_id, a.site_id, sit.name AS site_name, a.status,
               a.resource_type, a.cld_public_id, a.captured_at, a.created_at
        FROM assets a
        LEFT JOIN sites sit ON sit.id = a.site_id
        WHERE {' AND '.join(where)}
        ORDER BY a.created_at DESC, a.id DESC
        LIMIT :limit
    """
    with _engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        tags_by_asset = _bulk_tags(conn, [r["id"] for r in rows])

    items = [_asset_card(r, tags_by_asset.get(str(r["id"]), [])) for r in rows]
    next_cursor = None
    if len(rows) == limit:
        last = rows[-1]
        next_cursor = _encode_cursor(last["created_at"], last["id"])
    return {"items": items, "next_cursor": next_cursor}


@router.get("/assets/{asset_id}")
def get_asset(asset_id: UUID) -> dict:
    with _engine().connect() as conn:
        row = _get_asset_row(conn, asset_id)
        tags = _asset_tags(conn, asset_id)
    return _asset_detail(row, tags)


@router.patch("/assets/{asset_id}")
def patch_asset(asset_id: UUID, body: AssetPatch) -> dict:
    fields = body.model_dump(exclude_unset=True)
    with _engine().begin() as conn:
        row = _get_asset_row(conn, asset_id)

        set_clauses: list[str] = []
        params: dict[str, Any] = {"id": str(asset_id)}

        if "captured_at" in fields:
            set_clauses += ["captured_at = :captured_at", "captured_at_source = 'manual'"]
            params["captured_at"] = fields["captured_at"]

        if fields.get("lat") is not None:
            set_clauses += ["lat = :lat", "lng = :lng", "location_source = 'manual'"]
            params["lat"] = fields["lat"]
            params["lng"] = fields["lng"]
            if not fields.get("site_id"):
                site_id = sites.assign_site(UUID(str(row["project_id"])), fields["lat"], fields["lng"])
                set_clauses.append("site_id = :computed_site_id")
                params["computed_site_id"] = str(site_id) if site_id else None

        if fields.get("site_id"):
            set_clauses.append("site_id = :site_id")
            params["site_id"] = str(fields["site_id"])

        if set_clauses:
            conn.execute(
                text(f"UPDATE assets SET {', '.join(set_clauses)}, updated_at = now() WHERE id = :id"),
                params,
            )

        for raw_tag in fields.get("add_tags") or []:
            t = raw_tag.strip().lower()
            if not t:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO asset_tags (asset_id, tag, source, score, rank)
                    VALUES (:asset_id, :tag, 'manual', NULL, NULL)
                    ON CONFLICT (asset_id, tag, source) DO NOTHING
                    """
                ),
                {"asset_id": str(asset_id), "tag": t},
            )

        for raw_tag in fields.get("remove_tags") or []:
            t = raw_tag.strip().lower()
            conn.execute(
                text(
                    "DELETE FROM asset_tags WHERE asset_id = :asset_id AND tag = :tag AND source = 'manual'"
                ),
                {"asset_id": str(asset_id), "tag": t},
            )

        row = _get_asset_row(conn, asset_id)
        tags = _asset_tags(conn, asset_id)
    return _asset_detail(row, tags)


@router.post("/assets/{asset_id}/reprocess", status_code=202)
def reprocess_asset(asset_id: UUID) -> dict:
    with _engine().connect() as conn:
        _get_asset_row(conn, asset_id)
    job_id = enqueue("analyze_asset", {"asset_id": str(asset_id)})
    return {"job_id": job_id}


@router.post("/search")
def do_search(body: SearchRequest) -> dict:
    hits = search_module.search(body)
    if not hits:
        return {"items": []}

    with _engine().connect() as conn:
        rows = conn.execute(
            text(f"{_ASSET_SELECT} WHERE a.id = ANY(CAST(:ids AS uuid[]))").bindparams(
                bindparam("ids", type_=ARRAY(String))
            ),
            {"ids": [str(h.asset_id) for h in hits]},
        ).mappings().all()
        tags_by_asset = _bulk_tags(conn, [r["id"] for r in rows])

    rows_by_id = {str(r["id"]): r for r in rows}
    items = []
    for h in hits:
        row = rows_by_id.get(str(h.asset_id))
        if row is None:
            continue
        items.append({"asset": _asset_card(row, tags_by_asset.get(str(row["id"]), [])), "score": h.score})
    return {"items": items}


@router.get("/jobs/{job_id}")
def get_job(job_id: int) -> dict:
    with _engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, kind, payload, status, attempts, max_attempts,
                       run_after, last_error, created_at, updated_at
                FROM jobs WHERE id = :id
                """
            ),
            {"id": job_id},
        ).mappings().first()
    if row is None:
        raise ApiError("NOT_FOUND", f"job {job_id} not found", 404)
    return dict(row)

from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.config import settings
from app.core.db import get_engine
from app.core.errors import ApiError
from app.core.jobs import enqueue
from app.fieldproof import assets as assets_module
from app.fieldproof import change, cloudinary_gw, lineage, sites, urls
from app.fieldproof import pairs as pairs_module
from app.fieldproof import search as search_module

log = logging.getLogger("fieldproof.routes")
from app.fieldproof.schemas import (
    AssetPatch,
    AssetRegister,
    ComparisonCreate,
    ProjectCreate,
    ReportCreate,
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


@router.get("/sites/{site_id}/pair-suggestions")
def pair_suggestions(site_id: UUID) -> dict:
    with _engine().connect() as conn:
        row = conn.execute(
            text(f"{_SITE_SELECT} WHERE s.id = :id GROUP BY s.id"),
            {"id": str(site_id)},
        ).mappings().first()
        if row is None:
            raise ApiError("NOT_FOUND", f"site {site_id} not found", 404)

        candidates = pairs_module.pair_suggestions(site_id)
        asset_ids = [c.before_id for c in candidates] + [c.after_id for c in candidates]
        rows = (
            conn.execute(
                text(f"{_ASSET_SELECT} WHERE a.id = ANY(CAST(:ids AS uuid[]))").bindparams(
                    bindparam("ids", type_=ARRAY(String))
                ),
                {"ids": [str(i) for i in asset_ids]},
            )
            .mappings()
            .all()
            if asset_ids
            else []
        )
        rows_by_id = {str(r["id"]): r for r in rows}
        tags_by_asset = _bulk_tags(conn, [r["id"] for r in rows])

    items = []
    for c in candidates:
        before_row = rows_by_id.get(str(c.before_id))
        after_row = rows_by_id.get(str(c.after_id))
        if before_row is None or after_row is None:
            continue
        items.append(
            {
                "before": _asset_card(before_row, tags_by_asset.get(str(before_row["id"]), [])),
                "after": _asset_card(after_row, tags_by_asset.get(str(after_row["id"]), [])),
                "image_similarity": c.image_similarity,
                "framing_warning": c.image_similarity < settings.framing_sim_threshold,
                "days_apart": c.days_apart,
            }
        )
    return {"items": items}


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


# ---- comparisons --------------------------------------------------------------

_COMPARISON_SELECT = """
    SELECT c.*, sit.name AS site_name
    FROM comparisons c
    JOIN sites sit ON sit.id = c.site_id
"""


def _comparison_response(conn, comp_row) -> dict:
    before_row = _get_asset_row(conn, UUID(str(comp_row["before_asset_id"])))
    after_row = _get_asset_row(conn, UUID(str(comp_row["after_asset_id"])))
    tags_by_asset = _bulk_tags(conn, [before_row["id"], after_row["id"]])
    before_card = _asset_card(before_row, tags_by_asset.get(str(before_row["id"]), []))
    after_card = _asset_card(after_row, tags_by_asset.get(str(after_row["id"]), []))

    days_apart = None
    if before_row["captured_at"] and after_row["captured_at"]:
        days_apart = (after_row["captured_at"] - before_row["captured_at"]).days

    return {
        "id": str(comp_row["id"]),
        "site_id": str(comp_row["site_id"]),
        "site_name": comp_row["site_name"],
        "status": comp_row["status"],
        "before": before_card,
        "after": after_card,
        "before_compare_url": urls.compare_url(before_row),
        "after_compare_url": urls.compare_url(after_row),
        "before_mask_url": urls.mask_url(comp_row["before_mask_public_id"])
        if comp_row["before_mask_public_id"]
        else None,
        "after_mask_url": urls.mask_url(comp_row["after_mask_public_id"])
        if comp_row["after_mask_public_id"]
        else None,
        "image_similarity": comp_row["image_similarity"],
        "framing_warning": comp_row["framing_warning"],
        "before_green_pct_rounded": change.round5(comp_row["before_green_pct"])
        if comp_row["before_green_pct"] is not None
        else None,
        "after_green_pct_rounded": change.round5(comp_row["after_green_pct"])
        if comp_row["after_green_pct"] is not None
        else None,
        "delta_green_pct_rounded": comp_row["delta_green_pct_rounded"],
        "days_apart": days_apart,
        "description": comp_row["description"],
        "description_model": comp_row["description_model"],
        "created_at": comp_row["created_at"],
    }


@router.post("/comparisons", status_code=202)
def create_comparison(body: ComparisonCreate) -> dict:
    with _engine().begin() as conn:
        site = conn.execute(
            text(f"{_SITE_SELECT} WHERE s.id = :id GROUP BY s.id"), {"id": str(body.site_id)}
        ).mappings().first()
        if site is None:
            raise ApiError("NOT_FOUND", f"site {body.site_id} not found", 404)

        before_row = _get_asset_row(conn, body.before_asset_id)
        after_row = _get_asset_row(conn, body.after_asset_id)
        for label, row in (("before_asset_id", before_row), ("after_asset_id", after_row)):
            if row["status"] != "ready" or row["resource_type"] != "image":
                raise ApiError("VALIDATION_ERROR", f"{label} must be a ready image asset", 422)
            if str(row["site_id"]) != str(body.site_id):
                raise ApiError("VALIDATION_ERROR", f"{label} is not at site {body.site_id}", 422)

        sim_row = conn.execute(
            text(
                """
                SELECT 1 - (be.embedding <=> ae.embedding) AS image_similarity
                FROM asset_embeddings be, asset_embeddings ae
                WHERE be.asset_id = :before_id AND be.frame_s = 0
                  AND ae.asset_id = :after_id AND ae.frame_s = 0
                """
            ),
            {"before_id": str(body.before_asset_id), "after_id": str(body.after_asset_id)},
        ).mappings().first()
        if sim_row is None:
            raise ApiError("VALIDATION_ERROR", "both assets must have embeddings", 422)
        image_similarity = float(sim_row["image_similarity"])

        comparison_id = uuid4()
        conn.execute(
            text(
                """
                INSERT INTO comparisons (
                    id, site_id, before_asset_id, after_asset_id,
                    image_similarity, framing_warning, status
                ) VALUES (
                    :id, :site_id, :before_asset_id, :after_asset_id,
                    :image_similarity, :framing_warning, 'pending'
                )
                """
            ),
            {
                "id": str(comparison_id),
                "site_id": str(body.site_id),
                "before_asset_id": str(body.before_asset_id),
                "after_asset_id": str(body.after_asset_id),
                "image_similarity": image_similarity,
                "framing_warning": image_similarity < settings.framing_sim_threshold,
            },
        )
    job_id = enqueue("build_comparison", {"comparison_id": str(comparison_id)})
    return {"comparison_id": str(comparison_id), "status": "pending", "job_id": job_id}


@router.get("/comparisons/{comparison_id}")
def get_comparison(comparison_id: UUID) -> dict:
    with _engine().connect() as conn:
        row = conn.execute(
            text(f"{_COMPARISON_SELECT} WHERE c.id = :id"), {"id": str(comparison_id)}
        ).mappings().first()
        if row is None:
            raise ApiError("NOT_FOUND", f"comparison {comparison_id} not found", 404)
        return _comparison_response(conn, row)


@router.get("/sites/{site_id}/comparisons")
def list_site_comparisons(site_id: UUID) -> dict:
    with _engine().connect() as conn:
        site = conn.execute(
            text(f"{_SITE_SELECT} WHERE s.id = :id GROUP BY s.id"), {"id": str(site_id)}
        ).mappings().first()
        if site is None:
            raise ApiError("NOT_FOUND", f"site {site_id} not found", 404)
        rows = conn.execute(
            text(f"{_COMPARISON_SELECT} WHERE c.site_id = :site_id ORDER BY c.created_at DESC"),
            {"site_id": str(site_id)},
        ).mappings().all()
        items = [_comparison_response(conn, r) for r in rows]
    return {"items": items}


@router.get("/projects/{project_id}/comparisons")
def list_project_comparisons(project_id: UUID, status: str | None = None) -> dict:
    with _engine().connect() as conn:
        _get_project_row(conn, project_id)
        where = ["sit.project_id = :project_id"]
        params: dict[str, Any] = {"project_id": str(project_id)}
        if status is not None:
            where.append("c.status = :status")
            params["status"] = status
        sql = f"""
            SELECT c.*, sit.name AS site_name
            FROM comparisons c
            JOIN sites sit ON sit.id = c.site_id
            WHERE {' AND '.join(where)}
            ORDER BY c.created_at DESC
        """
        rows = conn.execute(text(sql), params).mappings().all()
        items = [_comparison_response(conn, r) for r in rows]
    return {"items": items}


# ---- reports --------------------------------------------------------------


def _report_response(conn, row) -> dict:
    item_rows = conn.execute(
        text(
            """
            SELECT position, kind, section, asset_id, comparison_id
            FROM report_items WHERE report_id = :id ORDER BY position
            """
        ),
        {"id": str(row["id"])},
    ).mappings().all()

    asset_ids = [r["asset_id"] for r in item_rows if r["asset_id"]]
    comparison_ids = [r["comparison_id"] for r in item_rows if r["comparison_id"]]

    assets_by_id: dict[str, dict] = {}
    if asset_ids:
        arows = conn.execute(
            text(f"{_ASSET_SELECT} WHERE a.id = ANY(CAST(:ids AS uuid[]))").bindparams(
                bindparam("ids", type_=ARRAY(String))
            ),
            {"ids": [str(i) for i in asset_ids]},
        ).mappings().all()
        tags_by_asset = _bulk_tags(conn, [r["id"] for r in arows])
        assets_by_id = {str(r["id"]): _asset_card(r, tags_by_asset.get(str(r["id"]), [])) for r in arows}

    comparisons_by_id: dict[str, dict] = {}
    if comparison_ids:
        crows = conn.execute(
            text(f"{_COMPARISON_SELECT} WHERE c.id = ANY(CAST(:ids AS uuid[]))").bindparams(
                bindparam("ids", type_=ARRAY(String))
            ),
            {"ids": [str(i) for i in comparison_ids]},
        ).mappings().all()
        comparisons_by_id = {str(r["id"]): _comparison_response(conn, r) for r in crows}

    items = [
        {
            "position": r["position"],
            "kind": r["kind"],
            "section": r["section"],
            "asset": assets_by_id.get(str(r["asset_id"])) if r["asset_id"] else None,
            "comparison": comparisons_by_id.get(str(r["comparison_id"])) if r["comparison_id"] else None,
        }
        for r in item_rows
    ]

    return {
        "id": str(row["id"]),
        "project_id": str(row["project_id"]),
        "status": row["status"],
        "date_from": row["date_from"].isoformat() if row["date_from"] else None,
        "date_to": row["date_to"].isoformat() if row["date_to"] else None,
        "metrics": row["metrics"] or {},
        "summary": row["summary"],
        "summary_model": row["summary_model"],
        "items": items,
        "created_at": row["created_at"],
    }


@router.post("/reports", status_code=202)
def create_report(body: ReportCreate) -> dict:
    with _engine().begin() as conn:
        _get_project_row(conn, body.project_id)
        if body.comparison_ids:
            rows = conn.execute(
                text(
                    """
                    SELECT c.id FROM comparisons c
                    JOIN sites sit ON sit.id = c.site_id
                    WHERE sit.project_id = :project_id AND c.status = 'ready'
                      AND c.id = ANY(CAST(:ids AS uuid[]))
                    """
                ).bindparams(bindparam("ids", type_=ARRAY(String))),
                {"project_id": str(body.project_id), "ids": [str(i) for i in body.comparison_ids]},
            ).mappings().all()
            found_ids = {str(r["id"]) for r in rows}
            missing = [str(i) for i in body.comparison_ids if str(i) not in found_ids]
            if missing:
                raise ApiError(
                    "VALIDATION_ERROR",
                    f"comparison_ids not found or not ready in this project: {missing}",
                    422,
                )

        report_id = uuid4()
        conn.execute(
            text(
                """
                INSERT INTO reports (id, project_id, date_from, date_to, status)
                VALUES (:id, :project_id, :date_from, :date_to, 'pending')
                """
            ),
            {
                "id": str(report_id),
                "project_id": str(body.project_id),
                "date_from": body.date_from,
                "date_to": body.date_to,
            },
        )
    job_id = enqueue(
        "generate_report",
        {"report_id": str(report_id), "comparison_ids": [str(i) for i in body.comparison_ids]},
    )
    return {"report_id": str(report_id), "status": "pending", "job_id": job_id}


@router.get("/reports/{report_id}")
def get_report(report_id: UUID) -> dict:
    with _engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM reports WHERE id = :id"), {"id": str(report_id)}
        ).mappings().first()
        if row is None:
            raise ApiError("NOT_FOUND", f"report {report_id} not found", 404)
        return _report_response(conn, row)


@router.get("/projects/{project_id}/reports")
def list_project_reports(project_id: UUID) -> dict:
    with _engine().connect() as conn:
        _get_project_row(conn, project_id)
        rows = conn.execute(
            text("SELECT * FROM reports WHERE project_id = :id ORDER BY created_at DESC"),
            {"id": str(project_id)},
        ).mappings().all()
        items = [_report_response(conn, r) for r in rows]
    return {"items": items}


# ---- campaign kit + lineage -------------------------------------------------


@router.get("/reports/{report_id}/campaign-kit")
def campaign_kit(report_id: UUID) -> dict:
    with _engine().connect() as conn:
        report_row = conn.execute(
            text("SELECT id FROM reports WHERE id = :id"), {"id": str(report_id)}
        ).mappings().first()
        if report_row is None:
            raise ApiError("NOT_FOUND", f"report {report_id} not found", 404)

        resp = cloudinary_gw.cached_usage()
        if resp is not None:
            log.info("cloudinary usage (campaign-kit credit guard): %s", resp)
            used_percent = (resp.get("credits") or {}).get("used_percent")
            if used_percent is not None and used_percent >= settings.credit_guard_percent:
                raise ApiError("CREDIT_GUARD", "cloudinary credit usage guard tripped", 503)

        item_rows = conn.execute(
            text(
                """
                SELECT position, kind, asset_id, comparison_id
                FROM report_items WHERE report_id = :id ORDER BY position
                """
            ),
            {"id": str(report_id)},
        ).mappings().all()

        evidence_asset_ids: list[UUID] = []
        seen: set[str] = set()
        for r in item_rows:
            if r["kind"] == "asset" and r["asset_id"] and str(r["asset_id"]) not in seen:
                seen.add(str(r["asset_id"]))
                evidence_asset_ids.append(r["asset_id"])
            if len(evidence_asset_ids) == 3:
                break
        comparison_ids = [r["comparison_id"] for r in item_rows if r["kind"] == "comparison" and r["comparison_id"]]

        items: list[dict] = []

        if comparison_ids:
            crows = conn.execute(
                text(f"{_COMPARISON_SELECT} WHERE c.id = ANY(CAST(:ids AS uuid[]))").bindparams(
                    bindparam("ids", type_=ARRAY(String))
                ),
                {"ids": [str(i) for i in comparison_ids]},
            ).mappings().all()
            for c in crows:
                before_row = _get_asset_row(conn, UUID(str(c["before_asset_id"])))
                after_row = _get_asset_row(conn, UUID(str(c["after_asset_id"])))
                items.append(
                    {
                        "kind": "collage",
                        "url": urls.collage_url(before_row, after_row),
                        "source_asset_ids": [str(before_row["id"]), str(after_row["id"])],
                        "transformation": "COLLAGE",
                    }
                )

        if evidence_asset_ids:
            arows = conn.execute(
                text(f"{_ASSET_SELECT} WHERE a.id = ANY(CAST(:ids AS uuid[]))").bindparams(
                    bindparam("ids", type_=ARRAY(String))
                ),
                {"ids": [str(i) for i in evidence_asset_ids]},
            ).mappings().all()
            rows_by_id = {str(r["id"]): r for r in arows}
            for asset_id in evidence_asset_ids:
                row = rows_by_id.get(str(asset_id))
                if row is None:
                    continue
                items.append(
                    {
                        "kind": "social_square",
                        "url": urls.square_url(row),
                        "source_asset_ids": [str(row["id"])],
                        "transformation": "SQUARE",
                    }
                )
                items.append(
                    {
                        "kind": "social_story",
                        "url": urls.story_url(row),
                        "source_asset_ids": [str(row["id"])],
                        "transformation": "STORY",
                    }
                )

        if not lineage.for_entity("kit", report_id):
            for item in items:
                lineage.record(
                    item["kind"],
                    item["url"],
                    sources=[UUID(i) for i in item["source_asset_ids"]],
                    tool="cloudinary",
                    transformation=item["transformation"],
                    entity=("kit", report_id),
                )

    return {"items": items}


_LINEAGE_ENTITY_TYPES = {"asset", "comparison", "report", "kit"}


def _lineage_dict(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "entity_type": row["entity_type"],
        "entity_id": str(row["entity_id"]),
        "output_kind": row["output_kind"],
        "output_ref": row["output_ref"],
        "source_asset_ids": [str(i) for i in (row["source_asset_ids"] or [])],
        "source_public_ids": row["source_public_ids"] or [],
        "source_versions": row["source_versions"] or [],
        "tool": row["tool"],
        "transformation": row["transformation"],
        "model": row["model"],
        "params": row["params"] or {},
        "created_at": row["created_at"],
    }


@router.get("/lineage")
def get_lineage(entity_type: str, entity_id: UUID) -> dict:
    if entity_type not in _LINEAGE_ENTITY_TYPES:
        raise ApiError("VALIDATION_ERROR", f"entity_type must be one of {sorted(_LINEAGE_ENTITY_TYPES)}", 422)
    records = lineage.for_entity(entity_type, entity_id)
    return {"items": [_lineage_dict(r) for r in records]}

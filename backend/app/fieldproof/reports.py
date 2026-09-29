"""Report metrics: pure SQL, no LLM or Cloudinary calls. See docs/04-roadmap.md T14."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY


def compute_metrics(
    conn,
    project_id: UUID,
    date_from: date,
    date_to: date,
    comparison_ids: list[UUID],
) -> dict[str, Any]:
    asset_rows = conn.execute(
        text(
            """
            SELECT id, resource_type, site_id, captured_at
            FROM assets
            WHERE project_id = :project_id AND status = 'ready'
              AND captured_at IS NOT NULL
              AND captured_at::date BETWEEN :date_from AND :date_to
            """
        ),
        {"project_id": str(project_id), "date_from": date_from, "date_to": date_to},
    ).mappings().all()

    assets_total = len(asset_rows)
    images = sum(1 for r in asset_rows if r["resource_type"] == "image")
    videos = sum(1 for r in asset_rows if r["resource_type"] == "video")
    sites_with_evidence = len({str(r["site_id"]) for r in asset_rows if r["site_id"]})
    captured_ats = [r["captured_at"] for r in asset_rows if r["captured_at"]]
    first_capture = min(captured_ats).date().isoformat() if captured_ats else None
    last_capture = max(captured_ats).date().isoformat() if captured_ats else None

    asset_ids = [r["id"] for r in asset_rows]
    top_activities: list[dict[str, Any]] = []
    detections: list[dict[str, Any]] = []
    if asset_ids:
        top_activities = [
            {"tag": r["tag"], "count": int(r["count"])}
            for r in conn.execute(
                text(
                    """
                    SELECT tag, COUNT(*) AS count
                    FROM asset_tags
                    WHERE asset_id = ANY(CAST(:ids AS uuid[])) AND source = 'clip' AND rank = 1
                    GROUP BY tag ORDER BY count DESC, tag LIMIT 5
                    """
                ).bindparams(bindparam("ids", type_=ARRAY(String))),
                {"ids": [str(i) for i in asset_ids]},
            ).mappings().all()
        ]
        detections = [
            {"tag": r["tag"], "count": int(r["count"])}
            for r in conn.execute(
                text(
                    """
                    SELECT tag, COUNT(*) AS count
                    FROM asset_tags
                    WHERE asset_id = ANY(CAST(:ids AS uuid[])) AND source = 'cld_detection'
                    GROUP BY tag ORDER BY count DESC, tag LIMIT 5
                    """
                ).bindparams(bindparam("ids", type_=ARRAY(String))),
                {"ids": [str(i) for i in asset_ids]},
            ).mappings().all()
        ]

    comparisons: list[dict[str, Any]] = []
    if comparison_ids:
        crows = conn.execute(
            text(
                """
                SELECT c.id, sit.name AS site_name, c.delta_green_pct_rounded,
                       ba.captured_at AS before_captured_at, aa.captured_at AS after_captured_at
                FROM comparisons c
                JOIN sites sit ON sit.id = c.site_id
                JOIN assets ba ON ba.id = c.before_asset_id
                JOIN assets aa ON aa.id = c.after_asset_id
                WHERE c.id = ANY(CAST(:ids AS uuid[]))
                ORDER BY c.created_at
                """
            ).bindparams(bindparam("ids", type_=ARRAY(String))),
            {"ids": [str(i) for i in comparison_ids]},
        ).mappings().all()
        for r in crows:
            days_apart = None
            if r["before_captured_at"] and r["after_captured_at"]:
                days_apart = (r["after_captured_at"] - r["before_captured_at"]).days
            comparisons.append(
                {
                    "id": str(r["id"]),
                    "site_name": r["site_name"],
                    "delta_green_pct_rounded": r["delta_green_pct_rounded"],
                    "days_apart": days_apart,
                }
            )

    return {
        "assets_total": assets_total,
        "images": images,
        "videos": videos,
        "sites_with_evidence": sites_with_evidence,
        "first_capture": first_capture,
        "last_capture": last_capture,
        "top_activities": top_activities,
        "detections": detections,
        "comparisons": comparisons,
    }


def select_evidence_assets(
    conn,
    project_id: UUID,
    date_from: date,
    date_to: date,
    tag: str,
    limit: int = 2,
) -> list[UUID]:
    """The `limit` highest-scoring ready assets in range whose rank-1 clip tag is `tag`."""
    rows = conn.execute(
        text(
            """
            SELECT t.asset_id
            FROM asset_tags t
            JOIN assets a ON a.id = t.asset_id
            WHERE a.project_id = :project_id AND a.status = 'ready'
              AND a.captured_at IS NOT NULL AND a.captured_at::date BETWEEN :date_from AND :date_to
              AND t.source = 'clip' AND t.rank = 1 AND t.tag = :tag
            ORDER BY t.score DESC NULLS LAST
            LIMIT :limit
            """
        ),
        {"project_id": str(project_id), "date_from": date_from, "date_to": date_to, "tag": tag, "limit": limit},
    ).mappings().all()
    return [UUID(str(r["asset_id"])) for r in rows]


def summary_placeholders(metrics: dict[str, Any]) -> dict[str, str | int | float]:
    # Values carry their own nouns/units so the model can't drop or misstate them.
    def count(n: int, singular: str, plural: str) -> str:
        return f"{n} {singular if n == 1 else plural}"

    placeholders: dict[str, str | int | float] = {
        "assets_total": count(metrics["assets_total"], "photo or video", "photos and videos"),
        "sites": count(metrics["sites_with_evidence"], "site", "sites"),
    }
    if metrics["top_activities"]:
        placeholders["top1_tag"] = metrics["top_activities"][0]["tag"].replace("_", " ")
        placeholders["top1_count"] = count(metrics["top_activities"][0]["count"], "photo", "photos")
    for i, comp in enumerate(metrics["comparisons"], start=1):
        placeholders[f"c{i}_site"] = comp["site_name"]
        delta = comp["delta_green_pct_rounded"]
        placeholders[f"c{i}_delta"] = f"{delta:+d} percentage points" if delta is not None else "no measurable change"
    return placeholders


def template_headline(metrics: dict[str, Any]) -> str:
    return f"{metrics['assets_total']} field assets across {metrics['sites_with_evidence']} sites"


def template_paragraphs(metrics: dict[str, Any]) -> list[str]:
    paragraphs = [
        (
            f"This report covers {metrics['assets_total']} field assets "
            f"({metrics['images']} images, {metrics['videos']} videos) across "
            f"{metrics['sites_with_evidence']} sites, captured between "
            f"{metrics['first_capture'] or 'an unknown date'} and {metrics['last_capture'] or 'an unknown date'}."
        )
    ]
    if metrics["top_activities"]:
        top = metrics["top_activities"][0]
        paragraphs.append(f"The most common activity observed was '{top['tag']}' ({top['count']} assets).")
    else:
        paragraphs.append("No dominant activity tag was detected in this period.")
    if metrics["comparisons"]:
        paragraphs.append(
            f"{len(metrics['comparisons'])} before/after comparison(s) were included, showing "
            "measurable change in green cover at each site."
        )
    return paragraphs[:3]


def template_highlights(metrics: dict[str, Any]) -> list[str]:
    highlights = [
        f"{metrics['assets_total']} assets analyzed",
        f"{metrics['sites_with_evidence']} sites covered",
    ]
    if metrics["top_activities"]:
        top = metrics["top_activities"][0]
        highlights.append(f"top activity: {top['tag']} ({top['count']})")
    else:
        highlights.append("no dominant activity detected")
    for comp in metrics["comparisons"][:2]:
        delta = comp["delta_green_pct_rounded"]
        if delta is not None:
            highlights.append(f"{comp['site_name']}: {delta:+d} points green cover")
    return highlights[:5]

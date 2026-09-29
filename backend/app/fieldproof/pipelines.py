from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core import llm
from app.core.config import CLIP_VISION_MODEL, settings
from app.core.db import get_engine
from app.core.errors import PermanentError, RetryableError
from app.fieldproof import (
    change,
    cloudinary_gw,
    embeddings,
    lineage,
    metadata,
    reports,
    sites,
    urls,
)
from app.fieldproof.transforms import NamedTransform

log = logging.getLogger("fieldproof.pipelines")

DETECTION_MIN_CONF = 0.6

CHANGE_DESCRIPTION_TEMPLATE = (
    "At {site}, estimated green cover changed from {before}% to {after}% ({delta} points) over {days} days."
)

CHANGE_DESCRIPTION_PROMPT = (
    "Write ONE short sentence for a conservation report describing a change in green vegetation "
    "cover at a site. You MUST use these exact placeholder tokens in your sentence instead of any "
    "literal numbers: {site} (site name), {before} and {after} (estimated green cover, in percent), "
    "{delta} (signed change in percentage points), {days} (days between the two photos). Never write a "
    "digit yourself; the placeholders are substituted afterward with the real values. Say the cover is "
    "estimated, report a decrease as a decrease, and do not invent causes. "
    'Respond with JSON only: {"sentence": "..."}.'
)


class ChangeDescription(BaseModel):
    sentence: str


class ReportSummary(BaseModel):
    headline: str
    paragraphs: list[str] = Field(min_length=2, max_length=3)
    highlights: list[str] = Field(min_length=3, max_length=5)


def _placeholder_meaning(name: str) -> str:
    if name == "assets_total":
        return "how many field photos and videos were analysed (already includes the noun)"
    if name == "sites":
        return "how many sites have evidence (already includes the noun)"
    if name == "top1_tag":
        return "the most frequent AI-detected tag in the photos (an observation, not necessarily good news)"
    if name == "top1_count":
        return "how many photos carry that tag (already includes the noun)"
    if name.endswith("_site"):
        return "name of a site with a before/after comparison"
    if name.endswith("_delta"):
        return (
            f"change in ESTIMATED green vegetation cover at {{{name.removesuffix('_delta')}_site}} "
            "(already signed and includes its unit)"
        )
    return "a measured value"


def _report_summary_prompt(placeholders: dict[str, Any]) -> str:
    legend = "\n".join(f"- {{{k}}}: {_placeholder_meaning(k)}" for k in placeholders)
    return (
        "Write a short, factual summary for an NGO field-evidence report.\n"
        "Placeholder tokens and what they mean:\n"
        f"{legend}\n"
        "Rules:\n"
        "- Use ONLY these tokens for every number and site name; never write a digit or a proper name yourself.\n"
        "- Tokens marked as including their noun or unit must not get another one after them.\n"
        "- Describe green-cover changes as \"estimated green cover\" in \"percentage points\". "
        "Report decreases as decreases; do not spin them as positive.\n"
        "- Do not invent causes, outcomes, people or programmes that the metrics do not state.\n"
        "- Plain, neutral language; no marketing words.\n"
        'Respond with JSON only: {"headline": "...", "paragraphs": ["...", "..."], '
        '"highlights": ["...", "...", "..."]}. The headline is under 10 words. paragraphs must have 2 to 3 '
        "entries; highlights must have 3 to 5 entries."
    )


def analyze_asset(payload: dict[str, Any]) -> None:
    asset_id = UUID(str(payload["asset_id"]))
    engine = get_engine()
    if engine is None:
        raise RetryableError("database not configured")

    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT * FROM assets WHERE id = :id"),
                {"id": str(asset_id)},
            ).mappings().first()
            if row is None:
                raise PermanentError(f"asset {asset_id} not found")
            project = conn.execute(
                text("SELECT started_on FROM projects WHERE id = :id"),
                {"id": str(row["project_id"])},
            ).mappings().first()
            conn.execute(
                text(
                    """
                    UPDATE assets
                    SET status = 'processing', error = NULL, updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": str(asset_id)},
            )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

    started_on = project["started_on"] if project else None
    resource_type = row["resource_type"]
    public_id = row["cld_public_id"]

    if row["media_metadata"] is not None:
        resource: dict[str, Any] = {}
        image_metadata = row["media_metadata"] or {}
        detection = row["cld_detection"] or {}
    else:
        try:
            resource = cloudinary_gw.get_resource(public_id, resource_type)
        except PermanentError as exc:
            _mark_failed(asset_id, str(exc))
            raise
        except RetryableError:
            raise
        image_metadata = resource.get("media_metadata") or resource.get("image_metadata") or {}
        detection = _detection_node(resource)

    parsed = metadata.parse_media_metadata(
        {"image_metadata": image_metadata},
        upload_time=row["created_at"] or datetime.now(timezone.utc),
        project_started_on=started_on,
        device_lat=payload.get("device_lat"),
        device_lng=payload.get("device_lng"),
    )

    try:
        frames = _load_frames(row, resource)
    except PermanentError:
        _mark_failed(asset_id, "undecodable image")
        raise
    except Exception as exc:
        raise RetryableError(str(exc)) from exc

    vecs = embeddings.embed_images(frames)
    mean_vec = embeddings.l2(vecs.mean(axis=0))
    clip_tags = embeddings.zero_shot(mean_vec)
    det_tags = _detection_tags(detection)

    if row["location_source"] == "manual":
        site_id = UUID(str(row["site_id"])) if row["site_id"] else None
        upd_lat, upd_lng, upd_location_source = row["lat"], row["lng"], row["location_source"]
    else:
        site_id = sites.assign_site(UUID(str(row["project_id"])), parsed.lat, parsed.lng)
        upd_lat, upd_lng, upd_location_source = parsed.lat, parsed.lng, parsed.location_source

    if row["captured_at_source"] == "manual":
        upd_captured_at, upd_captured_at_source = row["captured_at"], row["captured_at_source"]
    else:
        upd_captured_at, upd_captured_at_source = parsed.captured_at, parsed.captured_at_source

    analysis_url = cloudinary_gw.url(public_id, NamedTransform.ANALYSIS, resource_type="image")
    if resource_type == "video":
        analysis_url = cloudinary_gw.url(
            public_id, NamedTransform.VIDEO_FRAME, resource_type="video", t=_frame_offsets(row)[0]
        )

    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM asset_embeddings WHERE asset_id = :id"),
                {"id": str(asset_id)},
            )
            conn.execute(
                text("DELETE FROM asset_tags WHERE asset_id = :id AND source IN ('clip','cld_detection')"),
                {"id": str(asset_id)},
            )
            for i, vec in enumerate(vecs):
                frame_s = 0.0 if resource_type == "image" else _frame_offsets(row)[i]
                conn.execute(
                    text(
                        """
                        INSERT INTO asset_embeddings (asset_id, frame_s, embedding, model)
                        VALUES (:asset_id, :frame_s, CAST(:embedding AS vector), :model)
                        """
                    ),
                    {
                        "asset_id": str(asset_id),
                        "frame_s": frame_s,
                        "embedding": _vec_literal(vec),
                        "model": CLIP_VISION_MODEL,
                    },
                )
            for tag in clip_tags:
                conn.execute(
                    text(
                        """
                        INSERT INTO asset_tags (asset_id, tag, source, score, rank)
                        VALUES (:asset_id, :tag, 'clip', :score, :rank)
                        """
                    ),
                    {
                        "asset_id": str(asset_id),
                        "tag": tag.tag,
                        "score": tag.score,
                        "rank": tag.rank,
                    },
                )
            for name, score in det_tags:
                conn.execute(
                    text(
                        """
                        INSERT INTO asset_tags (asset_id, tag, source, score, rank)
                        VALUES (:asset_id, :tag, 'cld_detection', :score, NULL)
                        ON CONFLICT (asset_id, tag, source) DO UPDATE SET score = EXCLUDED.score
                        """
                    ),
                    {"asset_id": str(asset_id), "tag": name, "score": score},
                )
            conn.execute(
                text(
                    """
                    UPDATE assets SET
                        status = 'ready',
                        error = NULL,
                        site_id = :site_id,
                        captured_at = :captured_at,
                        captured_at_source = :captured_at_source,
                        lat = COALESCE(:lat, lat),
                        lng = COALESCE(:lng, lng),
                        location_source = :location_source,
                        media_metadata = CAST(:media_metadata AS jsonb),
                        cld_detection = CAST(:cld_detection AS jsonb),
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(asset_id),
                    "site_id": str(site_id) if site_id else None,
                    "captured_at": upd_captured_at,
                    "captured_at_source": upd_captured_at_source,
                    "lat": upd_lat,
                    "lng": upd_lng,
                    "location_source": upd_location_source,
                    "media_metadata": _json(image_metadata),
                    "cld_detection": _json(detection),
                },
            )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

    lineage.delete_for("asset", asset_id, ["analysis", "embedding", "tags"])
    lineage.record(
        "analysis",
        analysis_url,
        sources=[asset_id],
        tool="cloudinary",
        transformation="c_limit,w_1024/f_jpg",
        entity=("asset", asset_id),
        source_public_ids=[public_id],
        source_versions=[int(row["cld_version"])],
    )
    lineage.record(
        "embedding",
        f"db:asset_embeddings:{asset_id}",
        sources=[asset_id],
        tool="clip",
        model=CLIP_VISION_MODEL,
        entity=("asset", asset_id),
        params={"frames": len(vecs)},
    )
    lineage.record(
        "tags",
        f"db:asset_tags:{asset_id}",
        sources=[asset_id],
        tool="clip",
        model=CLIP_VISION_MODEL,
        entity=("asset", asset_id),
        params={"labels": "labels_v1", "clip": [t.tag for t in clip_tags]},
    )


def _load_frames(row, resource: dict) -> list[Image.Image]:
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass

    if row["resource_type"] == "video":
        urls = [
            cloudinary_gw.url(
                row["cld_public_id"],
                NamedTransform.VIDEO_FRAME,
                resource_type="video",
                t=t,
                format="jpg",
            )
            for t in _frame_offsets(row)
        ]
    else:
        urls = [
            cloudinary_gw.url(
                row["cld_public_id"], NamedTransform.ANALYSIS, resource_type="image"
            )
        ]
    frames: list[Image.Image] = []
    for u in urls:
        img = _download_image(u)
        frames.append(img)
    if not frames:
        raise PermanentError("no frames decoded")
    return frames


def _frame_offsets(row) -> list[float]:
    duration = float(row["duration_s"] or 0)
    if duration <= 0:
        return [0.0, 0.0, 0.0]
    end_cap = max(duration - 0.5, 0.0)
    pts = [duration * 0.10, duration * 0.50, duration * 0.90]
    return [min(p, end_cap) for p in pts]


def _download_image(url: str) -> Image.Image:
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            res = client.get(url)
            res.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise PermanentError("image 404") from exc
        raise RetryableError(str(exc)) from exc
    except httpx.HTTPError as exc:
        raise RetryableError(str(exc)) from exc
    try:
        img = Image.open(io.BytesIO(res.content))
        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")
    except Exception as exc:
        raise PermanentError(f"undecodable image: {exc}") from exc


def _detection_node(resource: dict) -> dict:
    info = resource.get("info") or {}
    detection = info.get("detection") if isinstance(info, dict) else None
    if detection:
        log.info("cld detection keys: %s", list(detection)[:20] if isinstance(detection, dict) else type(detection))
        return detection if isinstance(detection, dict) else {"raw": detection}
    return {}


def _detection_tags(detection: dict) -> list[tuple[str, float]]:
    found: list[tuple[str, float]] = []

    def add(tag: Any, conf: Any) -> None:
        if not tag or conf is None:
            return
        try:
            score = float(conf)
        except (TypeError, ValueError):
            return
        if score > 1:
            score = score / 100.0
        if score >= DETECTION_MIN_CONF:
            found.append((str(tag).lower(), score))

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        # coco_v2's real shape: {"tags": {"<label>": [{"confidence": 95.3, ...}, ...]}}
        tags_node = node.get("tags")
        if isinstance(tags_node, dict):
            for label, dets in tags_node.items():
                dets_list = dets if isinstance(dets, list) else [dets]
                for det in dets_list:
                    if isinstance(det, dict):
                        add(label, det.get("confidence") or det.get("score") or det.get("percent"))
                    else:
                        add(label, det)
        # fallback shape some detection add-ons use: {"tag"/"name"/"label": ..., "confidence": ...}
        tag = node.get("tag") or node.get("name") or node.get("label")
        conf = node.get("confidence") or node.get("score") or node.get("percent")
        add(tag, conf)
        for val in node.values():
            walk(val)

    walk(detection)
    # unique by tag, keep max score
    best: dict[str, float] = {}
    for tag, score in found:
        best[tag] = max(score, best.get(tag, 0.0))
    return list(best.items())


def build_comparison(payload: dict[str, Any]) -> None:
    comparison_id = UUID(str(payload["comparison_id"]))
    engine = get_engine()
    if engine is None:
        raise RetryableError("database not configured")

    try:
        with engine.begin() as conn:
            comparison = conn.execute(
                text("SELECT * FROM comparisons WHERE id = :id"),
                {"id": str(comparison_id)},
            ).mappings().first()
            if comparison is None:
                raise PermanentError(f"comparison {comparison_id} not found")
            before_row = conn.execute(
                text("SELECT * FROM assets WHERE id = :id"),
                {"id": str(comparison["before_asset_id"])},
            ).mappings().first()
            after_row = conn.execute(
                text("SELECT * FROM assets WHERE id = :id"),
                {"id": str(comparison["after_asset_id"])},
            ).mappings().first()
            site = conn.execute(
                text("SELECT name FROM sites WHERE id = :id"),
                {"id": str(comparison["site_id"])},
            ).mappings().first()
            conn.execute(
                text("UPDATE comparisons SET status = 'processing' WHERE id = :id"),
                {"id": str(comparison_id)},
            )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

    if before_row is None or after_row is None:
        raise PermanentError("before/after asset not found")

    before_compare_url = cloudinary_gw.url(before_row["cld_public_id"], NamedTransform.COMPARE, resource_type="image")
    after_compare_url = cloudinary_gw.url(after_row["cld_public_id"], NamedTransform.COMPARE, resource_type="image")

    before_img = _download_image(before_compare_url)
    after_img = _download_image(after_compare_url)

    before_result = change.green_cover(before_img)
    after_result = change.green_cover(after_img)

    before_upload = cloudinary_gw.upload_derived(
        before_result.mask_png,
        folder="fieldproof/derived/masks",
        public_id=f"{comparison_id}_before",
        overwrite=True,
    )
    after_upload = cloudinary_gw.upload_derived(
        after_result.mask_png,
        folder="fieldproof/derived/masks",
        public_id=f"{comparison_id}_after",
        overwrite=True,
    )
    before_mask_public_id = before_upload["public_id"]
    after_mask_public_id = after_upload["public_id"]

    before_rounded = change.round5(before_result.pct)
    after_rounded = change.round5(after_result.pct)
    delta_rounded = int(after_rounded - before_rounded)

    days_apart = (after_row["captured_at"] - before_row["captured_at"]).days
    site_name = site["name"] if site else "the site"
    description_placeholders = {
        "site": site_name,
        "before": int(before_rounded),
        "after": int(after_rounded),
        "delta": f"{delta_rounded:+d}",
        "days": days_apart,
    }
    description_template = ChangeDescription(
        sentence=CHANGE_DESCRIPTION_TEMPLATE.format(**description_placeholders)
    )
    description_result, description_model = llm.generate_text(
        task="change_description",
        prompt=CHANGE_DESCRIPTION_PROMPT,
        placeholders=description_placeholders,
        schema=ChangeDescription,
        template=description_template,
    )
    description = description_result.sentence

    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE comparisons SET
                        status = 'ready',
                        before_green_pct = :before_pct,
                        after_green_pct = :after_pct,
                        delta_green_pct_rounded = :delta_rounded,
                        before_mask_public_id = :before_mask_public_id,
                        after_mask_public_id = :after_mask_public_id,
                        description = :description,
                        description_model = :description_model
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(comparison_id),
                    "before_pct": before_result.pct,
                    "after_pct": after_result.pct,
                    "delta_rounded": delta_rounded,
                    "before_mask_public_id": before_mask_public_id,
                    "after_mask_public_id": after_mask_public_id,
                    "description": description,
                    "description_model": description_model,
                },
            )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

    lineage.delete_for("comparison", comparison_id, ["compare", "mask", "ai_text"])
    lineage.record(
        "compare",
        before_compare_url,
        sources=[UUID(str(before_row["id"]))],
        tool="cloudinary",
        transformation="c_fill,g_auto,w_800,h_600/f_jpg",
        entity=("comparison", comparison_id),
        source_public_ids=[before_row["cld_public_id"]],
        source_versions=[int(before_row["cld_version"])],
    )
    lineage.record(
        "compare",
        after_compare_url,
        sources=[UUID(str(after_row["id"]))],
        tool="cloudinary",
        transformation="c_fill,g_auto,w_800,h_600/f_jpg",
        entity=("comparison", comparison_id),
        source_public_ids=[after_row["cld_public_id"]],
        source_versions=[int(after_row["cld_version"])],
    )
    lineage.record(
        "mask",
        urls.mask_url(before_mask_public_id),
        sources=[UUID(str(before_row["id"]))],
        tool="pillow",
        entity=("comparison", comparison_id),
        params={
            "algorithm": "green_v1",
            "exg": settings.green_exg_threshold,
            "brightness": [20, 240],
            "roi": "bottom70",
        },
    )
    lineage.record(
        "mask",
        urls.mask_url(after_mask_public_id),
        sources=[UUID(str(after_row["id"]))],
        tool="pillow",
        entity=("comparison", comparison_id),
        params={
            "algorithm": "green_v1",
            "exg": settings.green_exg_threshold,
            "brightness": [20, 240],
            "roi": "bottom70",
        },
    )
    lineage.record(
        "ai_text",
        f"db:comparisons:{comparison_id}",
        sources=[UUID(str(before_row["id"])), UUID(str(after_row["id"]))],
        tool="llm",
        model=description_model,
        entity=("comparison", comparison_id),
        params={"task": "change_description"},
    )


def on_build_comparison_failed(payload: dict[str, Any], error: str) -> None:
    _mark_comparison_failed(UUID(str(payload["comparison_id"])), error)


def _mark_comparison_failed(comparison_id: UUID, error: str) -> None:
    engine = get_engine()
    if engine is None:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE comparisons SET status = 'failed' WHERE id = :id"),
                {"id": str(comparison_id)},
            )
    except OperationalError:
        log.exception("could not mark comparison %s failed", comparison_id)


def on_analyze_asset_failed(payload: dict[str, Any], error: str) -> None:
    _mark_failed(UUID(str(payload["asset_id"])), error)


def _mark_failed(asset_id: UUID, error: str) -> None:
    engine = get_engine()
    if engine is None:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE assets
                    SET status = 'failed', error = :error, updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": str(asset_id), "error": error[:2000]},
            )
    except OperationalError:
        log.exception("could not mark asset %s failed", asset_id)


def generate_report(payload: dict[str, Any]) -> None:
    report_id = UUID(str(payload["report_id"]))
    comparison_ids = [UUID(str(i)) for i in payload.get("comparison_ids", [])]
    engine = get_engine()
    if engine is None:
        raise RetryableError("database not configured")

    try:
        with engine.begin() as conn:
            report = conn.execute(
                text("SELECT * FROM reports WHERE id = :id"), {"id": str(report_id)}
            ).mappings().first()
            if report is None:
                raise PermanentError(f"report {report_id} not found")
            conn.execute(
                text("UPDATE reports SET status = 'processing' WHERE id = :id"),
                {"id": str(report_id)},
            )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

    project_id = UUID(str(report["project_id"]))
    date_from = report["date_from"]
    date_to = report["date_to"]

    try:
        with engine.connect() as conn:
            metrics = reports.compute_metrics(conn, project_id, date_from, date_to, comparison_ids)

            report_items: list[dict[str, Any]] = []
            for activity in metrics["top_activities"]:
                for asset_id in reports.select_evidence_assets(
                    conn, project_id, date_from, date_to, activity["tag"], limit=2
                ):
                    report_items.append(
                        {"kind": "asset", "asset_id": asset_id, "comparison_id": None, "section": "activities"}
                    )
            for comp in metrics["comparisons"]:
                report_items.append(
                    {
                        "kind": "comparison",
                        "asset_id": None,
                        "comparison_id": UUID(comp["id"]),
                        "section": "before_after",
                    }
                )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

    placeholders = reports.summary_placeholders(metrics)
    template = ReportSummary(
        headline=reports.template_headline(metrics),
        paragraphs=reports.template_paragraphs(metrics),
        highlights=reports.template_highlights(metrics),
    )
    summary_result, summary_model = llm.generate_text(
        task="report_summary",
        prompt=_report_summary_prompt(placeholders),
        placeholders=placeholders,
        schema=ReportSummary,
        template=template,
    )

    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM report_items WHERE report_id = :id"), {"id": str(report_id)})
            for position, item in enumerate(report_items):
                conn.execute(
                    text(
                        """
                        INSERT INTO report_items (report_id, position, kind, asset_id, comparison_id, section)
                        VALUES (:report_id, :position, :kind, :asset_id, :comparison_id, :section)
                        """
                    ),
                    {
                        "report_id": str(report_id),
                        "position": position,
                        "kind": item["kind"],
                        "asset_id": str(item["asset_id"]) if item["asset_id"] else None,
                        "comparison_id": str(item["comparison_id"]) if item["comparison_id"] else None,
                        "section": item["section"],
                    },
                )
            conn.execute(
                text(
                    """
                    UPDATE reports SET
                        status = 'ready',
                        metrics = CAST(:metrics AS jsonb),
                        summary = CAST(:summary AS jsonb),
                        summary_model = :summary_model
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(report_id),
                    "metrics": _json(metrics),
                    "summary": _json(summary_result.model_dump()),
                    "summary_model": summary_model,
                },
            )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

    lineage.delete_for("report", report_id, ["ai_text"])
    lineage.record(
        "ai_text",
        f"db:reports:{report_id}",
        sources=[],
        tool="llm",
        model=summary_model,
        entity=("report", report_id),
        params={"task": "report_summary"},
    )


def on_generate_report_failed(payload: dict[str, Any], error: str) -> None:
    _mark_report_failed(UUID(str(payload["report_id"])), error)


def _mark_report_failed(report_id: UUID, error: str) -> None:
    engine = get_engine()
    if engine is None:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE reports SET status = 'failed' WHERE id = :id"),
                {"id": str(report_id)},
            )
    except OperationalError:
        log.exception("could not mark report %s failed", report_id)


def _vec_literal(vec: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec.tolist()) + "]"


def _json(obj: Any) -> str:
    import json

    return json.dumps(obj)

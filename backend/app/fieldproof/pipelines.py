from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import numpy as np
from PIL import Image, ImageOps
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import CLIP_VISION_MODEL
from app.core.db import get_engine
from app.core.errors import PermanentError, RetryableError
from app.fieldproof import cloudinary_gw, embeddings, lineage, metadata, sites
from app.fieldproof.transforms import NamedTransform

log = logging.getLogger("fieldproof.pipelines")

DETECTION_MIN_CONF = 0.6


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

    try:
        resource = cloudinary_gw.get_resource(public_id, resource_type)
    except PermanentError as exc:
        _mark_failed(asset_id, str(exc))
        raise
    except RetryableError:
        raise

    image_metadata = resource.get("image_metadata") or {}
    detection = _detection_node(resource)
    parsed = metadata.parse_media_metadata(
        {"image_metadata": image_metadata, **resource},
        upload_time=row["created_at"] or datetime.now(timezone.utc),
        project_started_on=started_on,
        device_lat=payload.get("device_lat", row["lat"]),
        device_lng=payload.get("device_lng", row["lng"]),
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
    site_id = sites.assign_site(UUID(str(row["project_id"])), parsed.lat, parsed.lng)

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
                    "captured_at": parsed.captured_at,
                    "captured_at_source": parsed.captured_at_source,
                    "lat": parsed.lat,
                    "lng": parsed.lng,
                    "location_source": parsed.location_source,
                    "media_metadata": _json(image_metadata),
                    "cld_detection": _json(detection),
                },
            )
    except OperationalError as exc:
        raise RetryableError(str(exc)) from exc

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

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        tag = node.get("tag") or node.get("name") or node.get("label")
        conf = node.get("confidence") or node.get("score") or node.get("percent")
        if tag and conf is not None:
            try:
                score = float(conf)
            except (TypeError, ValueError):
                score = 0.0
            if score > 1:
                score = score / 100.0
            if score >= DETECTION_MIN_CONF:
                found.append((str(tag).lower(), score))
        for val in node.values():
            walk(val)

    walk(detection)
    # unique by tag, keep max score
    best: dict[str, float] = {}
    for tag, score in found:
        best[tag] = max(score, best.get(tag, 0.0))
    return list(best.items())


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


def _vec_literal(vec: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec.tolist()) + "]"


def _json(obj: Any) -> str:
    import json

    return json.dumps(obj)

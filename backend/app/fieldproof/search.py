from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.db import get_engine
from app.core.errors import ApiError
from app.fieldproof import embeddings
from app.fieldproof.schemas import SearchRequest

TAG_BOOST = 0.03
_CANDIDATE_MULTIPLIER = 3
_CANDIDATE_CAP = 200


@dataclass
class SearchHit:
    asset_id: UUID
    score: float


def search(req: SearchRequest) -> list[SearchHit]:
    engine = get_engine()
    if engine is None:
        raise ApiError("INTERNAL", "database not configured", 500)

    where = ["a.status = 'ready'"]
    params: dict[str, Any] = {}
    if req.project_id is not None:
        where.append("a.project_id = :project_id")
        params["project_id"] = str(req.project_id)
    if req.site_id is not None:
        where.append("a.site_id = :site_id")
        params["site_id"] = str(req.site_id)
    if req.tag is not None:
        where.append("EXISTS (SELECT 1 FROM asset_tags t WHERE t.asset_id = a.id AND t.tag = :tag)")
        params["tag"] = req.tag
    where_sql = " AND ".join(where)

    if not req.query.strip():
        return _browse(engine, where_sql, params, req.limit)
    return _semantic(engine, where_sql, params, req.query, req.limit)


def _browse(engine, where_sql: str, params: dict[str, Any], limit: int) -> list[SearchHit]:
    sql = f"""
        SELECT a.id
        FROM assets a
        WHERE {where_sql}
        ORDER BY a.captured_at DESC NULLS LAST, a.created_at DESC
        LIMIT :limit
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {**params, "limit": limit}).mappings().all()
    return [SearchHit(asset_id=UUID(str(r["id"])), score=0.0) for r in rows]


def _semantic(engine, where_sql: str, params: dict[str, Any], query: str, limit: int) -> list[SearchHit]:
    qvec = embeddings.embed_text(query)
    query_words = {w.lower() for w in query.split() if w}
    candidate_limit = min(limit * _CANDIDATE_MULTIPLIER, _CANDIDATE_CAP)

    sql = f"""
        WITH q AS (SELECT CAST(:qvec AS vector(512)) AS v)
        SELECT a.id, MAX(1 - (e.embedding <=> q.v)) AS score
        FROM assets a
        JOIN asset_embeddings e ON e.asset_id = a.id, q
        WHERE {where_sql}
        GROUP BY a.id
        ORDER BY score DESC
        LIMIT :limit
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql), {**params, "qvec": _vec_literal(qvec), "limit": candidate_limit}
        ).mappings().all()
        asset_ids = [r["id"] for r in rows]
        tags_by_asset = _bulk_tag_sets(conn, asset_ids)

    hits = []
    for r in rows:
        score = float(r["score"])
        tags = tags_by_asset.get(str(r["id"]), set())
        if query_words & tags:
            score += TAG_BOOST
        hits.append(SearchHit(asset_id=UUID(str(r["id"])), score=score))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


def _bulk_tag_sets(conn, asset_ids: list[Any]) -> dict[str, set[str]]:
    if not asset_ids:
        return {}
    rows = conn.execute(
        text(
            "SELECT asset_id, tag FROM asset_tags WHERE asset_id = ANY(CAST(:ids AS uuid[]))"
        ).bindparams(bindparam("ids", type_=ARRAY(String))),
        {"ids": [str(i) for i in asset_ids]},
    ).mappings().all()
    by_asset: dict[str, set[str]] = {}
    for r in rows:
        by_asset.setdefault(str(r["asset_id"]), set()).add(r["tag"])
    return by_asset


def _vec_literal(vec: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec.tolist()) + "]"

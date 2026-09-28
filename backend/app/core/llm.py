from __future__ import annotations

import hashlib
import json
import logging
import re

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.db import get_engine

log = logging.getLogger("fieldproof.llm")

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _model_chain() -> list[str]:
    chain: list[str] = []
    if settings.gemini_api_key:
        chain.append(settings.gemini_model)
    if settings.groq_api_key:
        chain.append("groq/openai/gpt-oss-20b")
    if settings.cerebras_api_key:
        chain.append("cerebras/gpt-oss-120b")
    return chain


def _cache_key(task: str, chain: list[str], prompt: str, placeholders: dict) -> str:
    payload = json.dumps(
        {"task": task, "chain": chain, "prompt": prompt, "placeholders": placeholders},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict | None:
    engine = get_engine()
    if engine is None:
        return None
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT response FROM llm_cache WHERE key = :key"),
                {"key": key},
            ).mappings().first()
    except OperationalError:
        return None
    return dict(row["response"]) if row else None


def _cache_set(key: str, model: str, response: dict) -> None:
    engine = get_engine()
    if engine is None:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO llm_cache (key, model, response)
                    VALUES (:key, :model, CAST(:response AS jsonb))
                    ON CONFLICT (key) DO NOTHING
                    """
                ),
                {"key": key, "model": model, "response": json.dumps(response)},
            )
    except OperationalError:
        log.warning("llm cache write failed", exc_info=True)


def _guard(data: dict, placeholders: dict) -> bool:
    """Reject any field that hardcodes a number instead of using a {placeholder} token."""
    for value in data.values():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not isinstance(item, str):
                continue
            for name in _PLACEHOLDER_RE.findall(item):
                if name not in placeholders:
                    return False
            stripped = _PLACEHOLDER_RE.sub("", item)
            if re.search(r"\d", stripped):
                return False
    return True


def _fill(data: dict, placeholders: dict[str, str | int | float]) -> dict:
    filled: dict = {}
    for key, value in data.items():
        if isinstance(value, list):
            filled[key] = [v.format_map(placeholders) if isinstance(v, str) else v for v in value]
        elif isinstance(value, str):
            filled[key] = value.format_map(placeholders)
        else:
            filled[key] = value
    return filled


def generate_text[T: BaseModel](
    task: str,
    prompt: str,
    placeholders: dict[str, str | int | float],
    schema: type[T],
    template: T,
) -> tuple[T, str]:
    chain = _model_chain()
    key = _cache_key(task, chain, prompt, placeholders)

    cached = _cache_get(key)
    if cached is not None:
        try:
            return schema.model_validate(cached["data"]), cached["model"]
        except Exception:
            log.warning("llm cache entry failed validation, ignoring", exc_info=True)

    if not chain:
        return template, "template"

    import litellm

    for attempt in range(2):
        try:
            response = litellm.completion(
                model=chain[0],
                fallbacks=chain[1:],
                response_format=schema,
                num_retries=2,
                timeout=20,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = json.loads(response.choices[0].message.content)
            if not _guard(raw, placeholders):
                log.warning("llm guard rejected response for task %s (attempt %d)", task, attempt)
                continue
            filled = _fill(raw, placeholders)
            result = schema.model_validate(filled)
            model_used = getattr(response, "model", chain[0]) or chain[0]
            _cache_set(key, model_used, {"data": filled, "model": model_used})
            return result, model_used
        except Exception:
            log.warning("llm generate_text failed for task %s (attempt %d)", task, attempt, exc_info=True)
            continue

    return template, "template"

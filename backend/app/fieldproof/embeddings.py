from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image

from app.core.config import CLIP_TEXT_MODEL, CLIP_VISION_MODEL, EMBED_DIM, settings

LABELS_V1: dict[str, str] = {
    "sapling": "young tree saplings",
    "mangrove": "a mangrove plantation",
    "flood": "a flooded area with standing water",
    "road_construction": "road construction work",
    "solar": "solar panels",
    "classroom": "children in a classroom",
    "hand_pump": "a village hand pump for drinking water",
    "waste": "a garbage dump full of waste",
    "cleanup": "volunteers cleaning up litter",
    "drought": "dry cracked earth from drought",
    "deforestation": "a deforested area with cut trees",
    "other_indoor": "an indoor office room",
    "other_city": "a city skyline",
    "other_person": "a close-up portrait of a person",
}

TEMPLATES = [
    "a photo of {}.",
    "a field photo of {}.",
    "a photo from an NGO project showing {}.",
]

NEGATIVE_PREFIX = "other_"


@dataclass
class TagScore:
    tag: str
    score: float
    rank: int


def l2(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n == 0:
        return v
    return v / n


@lru_cache
def _vision():
    from fastembed import ImageEmbedding

    return ImageEmbedding(CLIP_VISION_MODEL, cache_dir=str(settings.models_dir))


@lru_cache
def _text():
    from fastembed import TextEmbedding

    return TextEmbedding(CLIP_TEXT_MODEL, cache_dir=str(settings.models_dir))


@lru_cache
def _label_matrix() -> tuple[list[str], np.ndarray]:
    keys = list(LABELS_V1)
    rows = []
    for key in keys:
        phrase = LABELS_V1[key]
        vs = np.array(list(_text().embed([t.format(phrase) for t in TEMPLATES])))
        rows.append(l2(np.mean([l2(v) for v in vs], axis=0)))
    return keys, np.stack(rows, axis=0)


def embed_images(imgs: list[Image.Image]) -> np.ndarray:
    raw = list(_vision().embed(imgs, batch_size=16))
    vecs = np.array([l2(v) for v in raw], dtype=np.float32)
    if vecs.ndim != 2 or vecs.shape[1] != EMBED_DIM:
        raise RuntimeError(f"unexpected embedding shape {vecs.shape}")
    return vecs


def embed_text(q: str) -> np.ndarray:
    v = next(iter(_text().embed([q])))
    return l2(np.array(v, dtype=np.float32))


def zero_shot(vec: np.ndarray) -> list[TagScore]:
    keys, matrix = _label_matrix()
    v = l2(np.asarray(vec, dtype=np.float64))
    if v.ndim == 2:
        v = l2(v.mean(axis=0))
    sims = matrix @ v
    order = np.argsort(-sims)
    out: list[TagScore] = []
    rank = 1
    for idx in order:
        tag = keys[int(idx)]
        if tag.startswith(NEGATIVE_PREFIX):
            continue
        out.append(TagScore(tag=tag, score=float(sims[idx]), rank=rank))
        rank += 1
        if rank > 3:
            break
    return out

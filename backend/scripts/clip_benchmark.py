"""CLIP benchmark for FieldProof.

Answers the open questions before we build tagging/search/compare:
  1. How fast is CLIP on this laptop (model load, per-image, per-query)?
  2. Are fastembed CLIP vectors already L2-normalised?
  3. What cosine scores does zero-shot tagging produce, and how accurate is it?
  4. What image-image similarity separates "same scene" from "different scene"
     (the framing-mismatch threshold for before/after pairs)?

Run from backend/:
    uv run python scripts/clip_benchmark.py            # first run downloads models + samples
    uv run python scripts/clip_benchmark.py --offline  # later runs, no internet needed

Put your own photos (jpg/png/heic) in backend/samples/mine/ to include them.
Results are written to backend/bench-results/<hostname>-<timestamp>.json so both
teammates can commit and compare them.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import CLIP_TEXT_MODEL, CLIP_VISION_MODEL, EMBED_DIM  # noqa: E402

MODELS_DIR = BACKEND_DIR / "models"
PUBLIC_DIR = BACKEND_DIR / "samples" / "public"
MINE_DIR = BACKEND_DIR / "samples" / "mine"
RESULTS_DIR = BACKEND_DIR / "bench-results"

USER_AGENT = "FieldProofBenchmark/0.1 (Code Cubicle 6.0 hackathon; contact via GitHub)"

# Fixed Wikimedia Commons sample set: (commons title, expected label).
# All are public domain / CC0 / CC BY / CC BY-SA; attribution is written to CREDITS.md.
SAMPLES: list[tuple[str, str]] = [
    ("File:Tree Sapling in British Columbia, Canada 2019.jpg", "sapling"),
    ("File:Mangrove plantation.jpg", "mangrove"),
    ("File:Flooded Albizia Saman (rain tree) in the Mekong.jpg", "flood"),
    ("File:Road construction vehicle, Bangalore (2025).jpg", "road_construction"),
    ("File:Road construction in tea plantation JEG9546.jpg", "road_construction"),
    ("File:Field of Solar Panels near Ogwell.jpg", "solar"),
    ("File:Solar panel field works near Gitit2940.jpg", "solar"),
    ("File:Solar panel field works near Gitit2941.jpg", "solar"),
    ("File:A classroom of children from rural homes.jpg", "classroom"),
    ("File:A beautiful hand pump in village Bado, Sindh.jpg", "hand_pump"),
    ("File:Quibdo Garbage dump.jpg", "waste"),
    ("File:Volunteers participate in beach debris cleanup - 52752007055.jpg", "cleanup"),
    ("File:California Drought Dry Lakebed 2009.jpg", "drought"),
    ("File:Deforested area, Goldisthal, 2023-05-20.jpg", "deforestation"),
]

# Two shots of the same site from slightly different positions -> "same scene" reference pair.
SAME_SCENE_PAIRS = [
    ("File:Solar panel field works near Gitit2940.jpg", "File:Solar panel field works near Gitit2941.jpg"),
]

LABELS: dict[str, str] = {
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
    # Negative labels so CLIP has somewhere to put images that match nothing.
    "other_indoor": "an indoor office room",
    "other_city": "a city skyline",
    "other_person": "a close-up portrait of a person",
}

TEMPLATES = [
    "a photo of {}.",
    "a field photo of {}.",
    "a photo from an NGO project showing {}.",
]

SEARCH_QUERIES = [
    "planting new trees",
    "water problem in a village",
    "construction work on a road",
    "trash and pollution",
    "renewable energy",
]


def safe_name(title: str) -> str:
    stem = title.removeprefix("File:")
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in stem)


def _get_with_retry(client, url: str, **kwargs):
    """Wikimedia rate-limits bursts (429/503); back off and retry instead of crashing."""
    for attempt in range(5):
        res = client.get(url, **kwargs)
        if res.status_code == 200:
            return res
        wait = int(res.headers.get("retry-after", 0) or 0) or 2 ** (attempt + 1)
        print(f"    HTTP {res.status_code}, retrying in {wait}s")
        time.sleep(wait)
    return None


def download_samples() -> None:
    import httpx

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    credits = ["# Sample image credits (Wikimedia Commons)\n",
               "| File | Author | License | Source |", "|---|---|---|---|"]
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as client:
        for title, _ in SAMPLES:
            target = PUBLIC_DIR / safe_name(title)
            res = _get_with_retry(
                client,
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "titles": title, "prop": "imageinfo",
                    "iiprop": "url|extmetadata", "iiurlwidth": 1024, "format": "json",
                },
            )
            if res is None:
                print(f"  ! Commons API unavailable, skipping: {title}")
                continue
            page = next(iter(res.json()["query"]["pages"].values()))
            if "imageinfo" not in page:
                print(f"  ! not found on Commons, skipping: {title}")
                continue
            ii = page["imageinfo"][0]
            meta = ii.get("extmetadata", {})
            author = meta.get("Artist", {}).get("value", "unknown")
            author = author.replace("|", "/").replace("\n", " ")
            license_name = meta.get("LicenseShortName", {}).get("value", "unknown")
            credits.append(f"| {title} | {author} | {license_name} | {ii['descriptionurl']} |")
            if target.exists():
                continue
            print(f"  downloading {title}")
            img = _get_with_retry(client, ii.get("thumburl") or ii["url"])
            if img is None or not img.headers.get("content-type", "").startswith("image/"):
                print(f"  ! image download failed, skipping: {title}")
                continue
            target.write_bytes(img.content)
            time.sleep(1)  # stay polite to Wikimedia
    (PUBLIC_DIR / "CREDITS.md").write_text("\n".join(credits) + "\n")


def load_image(path: Path):
    from PIL import Image, ImageOps

    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # phone photos store rotation in EXIF
    img = img.convert("RGB")  # CLIP needs 3-channel RGB (PNG alpha / CMYK / palette break it)
    img.thumbnail((1024, 1024))
    return img


def l2(v):
    import numpy as np

    return v / np.linalg.norm(v)


def system_info() -> dict:
    cpu = platform.processor() or "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    ram_gb = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                ram_gb = round(int(line.split()[1]) / 1024 / 1024, 1)
    except OSError:
        pass
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu": cpu,
        "cpu_count": os.cpu_count(),
        "ram_gb": ram_gb,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="never touch the network (models + samples must exist)")
    args = parser.parse_args()

    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"

    import numpy as np
    from fastembed import ImageEmbedding, TextEmbedding

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass

    print("== FieldProof CLIP benchmark ==")
    info = system_info()
    print(f"machine: {info['cpu']} | {info['cpu_count']} cores | {info['ram_gb']} GB RAM")

    if not args.offline:
        print("-- samples")
        download_samples()

    public = [(PUBLIC_DIR / safe_name(t), t, lbl) for t, lbl in SAMPLES if (PUBLIC_DIR / safe_name(t)).exists()]
    mine = sorted(p for p in MINE_DIR.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".webp"})
    if not public and not mine:
        sys.exit("No images found. Run once without --offline to download samples.")

    print("-- loading models (first run downloads ~600 MB into backend/models/)")
    t0 = time.perf_counter()
    vision = ImageEmbedding(CLIP_VISION_MODEL, cache_dir=str(MODELS_DIR))
    text = TextEmbedding(CLIP_TEXT_MODEL, cache_dir=str(MODELS_DIR))
    load_s = time.perf_counter() - t0
    print(f"   loaded in {load_s:.1f}s")

    # --- image embedding speed ---
    all_paths = [p for p, _, _ in public] + mine
    t0 = time.perf_counter()
    images = [load_image(p) for p in all_paths]
    preprocess_ms = (time.perf_counter() - t0) * 1000 / len(images)

    first = images[0]
    t0 = time.perf_counter()
    list(vision.embed([first]))
    first_call_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    raw_vecs = list(vision.embed(images, batch_size=16))
    batch_ms = (time.perf_counter() - t0) * 1000 / len(images)

    t0 = time.perf_counter()
    list(vision.embed([first]))
    single_ms = (time.perf_counter() - t0) * 1000

    norms = [float(np.linalg.norm(v)) for v in raw_vecs]
    dims = {len(v) for v in raw_vecs}
    img_vecs = np.array([l2(v) for v in raw_vecs])

    # --- text embedding (prompt ensemble per label) ---
    t0 = time.perf_counter()
    label_vecs = {}
    for key, phrase in LABELS.items():
        vs = np.array(list(text.embed([t.format(phrase) for t in TEMPLATES])))
        label_vecs[key] = l2(np.mean([l2(v) for v in vs], axis=0))
    t0q = time.perf_counter()
    query_vecs = {q: l2(next(iter(text.embed([q])))) for q in SEARCH_QUERIES}
    query_ms = (time.perf_counter() - t0q) * 1000 / len(SEARCH_QUERIES)
    text_total_ms = (time.perf_counter() - t0) * 1000

    keys = list(label_vecs)
    L = np.array([label_vecs[k] for k in keys])
    sims = img_vecs @ L.T  # cosine, since everything is L2-normalised

    # --- zero-shot tagging on the labelled public set ---
    per_image, correct_scores, wrong_best = [], [], []
    top1 = top3 = 0
    names = [p.name for p in all_paths]
    for i, path in enumerate(all_paths):
        order = np.argsort(-sims[i])
        top = [(keys[j], round(float(sims[i][j]), 4)) for j in order[:3]]
        entry = {"image": path.name, "top3": top}
        if i < len(public):
            expected = public[i][2]
            entry["expected"] = expected
            exp_score = float(sims[i][keys.index(expected)])
            correct_scores.append(exp_score)
            best_other = max(float(sims[i][j]) for j, k in enumerate(keys) if k != expected)
            wrong_best.append(best_other)
            top1 += top[0][0] == expected
            top3 += expected in [k for k, _ in top]
        per_image.append(entry)

    # --- image-image similarity (framing threshold) ---
    img_sim = img_vecs @ img_vecs.T
    title_to_idx = {t: i for i, (_, t, _) in enumerate(public)}
    same_scene = [
        round(float(img_sim[title_to_idx[a]][title_to_idx[b]]), 4)
        for a, b in SAME_SCENE_PAIRS if a in title_to_idx and b in title_to_idx
    ]
    same_pairs = {tuple(sorted((title_to_idx.get(a), title_to_idx.get(b)))) for a, b in SAME_SCENE_PAIRS}
    diff_scene = [
        float(img_sim[i][j])
        for i in range(len(public)) for j in range(i + 1, len(public))
        if (i, j) not in same_pairs and public[i][2] != public[j][2]
    ]
    mine_pairs = [
        {"a": names[i], "b": names[j], "similarity": round(float(img_sim[i][j]), 4)}
        for i in range(len(public), len(all_paths)) for j in range(i + 1, len(all_paths))
    ]

    # --- semantic search sanity check ---
    search = {
        q: [(names[j], round(float(img_vecs[j] @ v), 4)) for j in np.argsort(-(img_vecs @ v))[:3]]
        for q, v in query_vecs.items()
    }

    def stats(xs):
        return {"min": round(min(xs), 4), "max": round(max(xs), 4), "mean": round(statistics.mean(xs), 4)} if xs else None

    n_pub = len(public)
    results = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "machine": info,
        "models": {"vision": CLIP_VISION_MODEL, "text": CLIP_TEXT_MODEL},
        "counts": {"public_images": n_pub, "my_images": len(mine)},
        "speed_ms": {
            "model_load_s": round(load_s, 2),
            "preprocess_per_image": round(preprocess_ms, 1),
            "first_embed_call": round(first_call_ms, 1),
            "per_image_batched": round(batch_ms, 1),
            "single_image_warm": round(single_ms, 1),
            "per_text_query": round(query_ms, 1),
            "all_text_embeddings_total": round(text_total_ms, 1),
        },
        "vectors": {
            "dims": sorted(dims),
            "dim_ok": dims == {EMBED_DIM},
            "raw_norm": stats(norms),
            "already_normalised": all(abs(n - 1) < 1e-3 for n in norms),
        },
        "zero_shot": {
            "top1_accuracy": round(top1 / n_pub, 3) if n_pub else None,
            "top3_accuracy": round(top3 / n_pub, 3) if n_pub else None,
            "correct_label_score": stats(correct_scores),
            "best_wrong_label_score": stats(wrong_best),
            "all_scores": stats([float(x) for x in sims.flatten()]),
            "per_image": per_image,
        },
        "image_similarity": {
            "same_scene_pairs": same_scene,
            "different_scene": stats(diff_scene),
            "my_photo_pairs": mine_pairs,
        },
        "search": search,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{info['hostname']}-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(results, indent=2))

    # --- human summary ---
    s = results["speed_ms"]
    z = results["zero_shot"]
    v = results["vectors"]
    print("\n== SPEED ==")
    print(f"model load            {s['model_load_s']} s")
    print(f"first embed call      {s['first_embed_call']} ms")
    print(f"per image (batched)   {s['per_image_batched']} ms")
    print(f"single image (warm)   {s['single_image_warm']} ms")
    print(f"per text query        {s['per_text_query']} ms")
    print("\n== VECTORS ==")
    print(f"dims {v['dims']} (expected {EMBED_DIM}) | raw norm {v['raw_norm']} | already normalised: {v['already_normalised']}")
    print("\n== ZERO-SHOT TAGGING ==")
    print(f"top-1 accuracy {z['top1_accuracy']} | top-3 accuracy {z['top3_accuracy']}")
    print(f"score of correct label  {z['correct_label_score']}")
    print(f"best wrong label score  {z['best_wrong_label_score']}")
    for e in per_image:
        mark = "" if "expected" not in e else ("OK " if e["top3"][0][0] == e["expected"] else "MISS ")
        exp = f" (expected {e['expected']})" if "expected" in e else " (yours)"
        print(f"  {mark}{e['image'][:48]:48s}{exp}: {e['top3']}")
    print("\n== IMAGE SIMILARITY (framing threshold) ==")
    print(f"same scene pairs        {same_scene}")
    print(f"different scenes        {results['image_similarity']['different_scene']}")
    for p in mine_pairs:
        print(f"  yours: {p['a']} <-> {p['b']}: {p['similarity']}")
    print("\n== SEARCH ==")
    for q, hits in search.items():
        print(f"  '{q}': {hits}")
    print(f"\nSaved: {out.relative_to(BACKEND_DIR)}")


if __name__ == "__main__":
    main()

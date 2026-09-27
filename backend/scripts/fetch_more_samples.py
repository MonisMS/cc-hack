"""T06: fetch ~5 more free-licensed Wikimedia Commons images per label, on top of
the 14 curated in scripts/clip_benchmark.py. Writes samples/public/labels.json
(filename -> label, covering ALL files) and appends to samples/public/CREDITS.md.

Run from backend/:
    uv run python scripts/fetch_more_samples.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from scripts.clip_benchmark import SAMPLES, USER_AGENT, _get_with_retry, safe_name  # noqa: E402

PUBLIC_DIR = BACKEND_DIR / "samples" / "public"
CREDITS_PATH = PUBLIC_DIR / "CREDITS.md"
LABELS_PATH = PUBLIC_DIR / "labels.json"
TARGET_PER_LABEL = 5
MAX_BYTES = 2 * 1024 * 1024
ALLOWED_FORMATS = {"jpg", "jpeg", "png", "webp"}

# Search terms per label; kept separate from the CLIP zero-shot phrases in clip_benchmark.py.
LABEL_QUERIES: dict[str, str] = {
    "sapling": "tree sapling planting",
    "mangrove": "mangrove plantation",
    "flood": "flooded road village",
    "road_construction": "road construction work",
    "solar": "solar panel farm",
    "classroom": "rural classroom children",
    "hand_pump": "village hand pump water",
    "waste": "garbage dump waste",
    "cleanup": "beach cleanup volunteers",
    "drought": "drought dry cracked earth",
    "deforestation": "deforestation cut trees",
}

ALLOWED_LICENSE_SUBSTRINGS = ("cc0", "public domain", "cc by", "pdm")


def _license_ok(license_name: str) -> bool:
    name = license_name.lower()
    return any(s in name for s in ALLOWED_LICENSE_SUBSTRINGS)


def search_candidates(client, query: str, limit: int = 20) -> list[str]:
    res = _get_with_retry(
        client,
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": f"{query} filetype:bitmap",
            "srnamespace": 6,
            "srlimit": limit,
            "format": "json",
        },
    )
    if res is None:
        return []
    return [hit["title"] for hit in res.json().get("query", {}).get("search", [])]


def fetch_image_info(client, title: str) -> dict | None:
    res = _get_with_retry(
        client,
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": 1600,
            "format": "json",
        },
    )
    if res is None:
        return None
    page = next(iter(res.json()["query"]["pages"].values()))
    if "imageinfo" not in page:
        return None
    return page["imageinfo"][0]


def _load_progress() -> dict[str, str]:
    existing_labels: dict[str, str] = {safe_name(title): label for title, label in SAMPLES}
    if LABELS_PATH.exists():
        existing_labels.update(json.loads(LABELS_PATH.read_text()))
    return existing_labels


def _save_progress(all_labels: dict[str, str]) -> None:
    LABELS_PATH.write_text(json.dumps(all_labels, indent=2, sort_keys=True) + "\n")


def _append_credit(row: str) -> None:
    with CREDITS_PATH.open("a") as f:
        f.write(row + "\n")


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    all_labels = _load_progress()  # resumable: survives an interrupted run
    _save_progress(all_labels)
    known_titles = {title for title, _ in SAMPLES}
    added_this_run = 0

    import httpx

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as client:
        for label, query in LABEL_QUERIES.items():
            already = sum(1 for v in all_labels.values() if v == label) - sum(
                1 for t, lbl in SAMPLES if lbl == label
            )
            if already >= TARGET_PER_LABEL:
                print(f"-- {label}: already have {already}/{TARGET_PER_LABEL}, skipping")
                continue
            print(f"-- {label}: searching '{query}' (have {already}/{TARGET_PER_LABEL})")
            found = already
            seen_titles: set[str] = set(known_titles)
            for title in search_candidates(client, query):
                if found >= TARGET_PER_LABEL:
                    break
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                fname = safe_name(title)
                if fname in all_labels:
                    continue  # already recorded (this run or a previous one)

                on_disk = (PUBLIC_DIR / fname).exists()

                info = fetch_image_info(client, title)
                if info is None:
                    continue
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                if ext not in ALLOWED_FORMATS:
                    continue
                if int(info.get("size") or 0) > 20 * 1024 * 1024:  # skip huge originals
                    continue

                meta = info.get("extmetadata", {})
                license_name = meta.get("LicenseShortName", {}).get("value", "unknown")
                if not _license_ok(license_name):
                    continue

                if not on_disk:
                    url = info.get("thumburl") or info.get("url")
                    img = _get_with_retry(client, url)
                    if img is None or not img.headers.get("content-type", "").startswith("image/"):
                        continue
                    if len(img.content) > MAX_BYTES:
                        continue
                    (PUBLIC_DIR / fname).write_bytes(img.content)

                author = meta.get("Artist", {}).get("value", "unknown")
                author = author.replace("|", "/").replace("\n", " ")
                _append_credit(f"| {title} | {author} | {license_name} | {info['descriptionurl']} |")
                all_labels[fname] = label
                _save_progress(all_labels)  # persist after every image, so interruption never loses progress
                found += 1
                added_this_run += 1
                print(f"   {'found' if on_disk else 'downloaded'} ({found}/{TARGET_PER_LABEL}): {title}")
                if not on_disk:
                    time.sleep(1)  # stay polite to Wikimedia

            if found < TARGET_PER_LABEL:
                print(f"   ! only found {found}/{TARGET_PER_LABEL} for '{label}'")

    print(f"\nAdded {added_this_run} new images this run. labels.json now has {len(all_labels)} entries.")


if __name__ == "__main__":
    main()

"""T07: rank-1 CLIP tag vs. expected label, for the seeded Wikimedia set.

Run from backend/:
    uv run python scripts/check_labels.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from app.core.db import get_engine  # noqa: E402
from scripts.seed_demo import slug  # noqa: E402

PUBLIC_DIR = BACKEND_DIR / "samples" / "public"
LABELS_PATH = PUBLIC_DIR / "labels.json"


def main() -> None:
    labels: dict[str, str] = json.loads(LABELS_PATH.read_text())
    expected_by_public_id = {slug(filename): label for filename, label in labels.items()}

    engine = get_engine()
    assert engine is not None
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT a.cld_public_id, t.tag
                FROM assets a
                JOIN asset_tags t ON t.asset_id = a.id AND t.source = 'clip' AND t.rank = 1
                WHERE a.cld_public_id = ANY(:pids)
                """
            ).bindparams(),
            {"pids": list(expected_by_public_id)},
        ).mappings().all()

    got_by_public_id = {r["cld_public_id"]: r["tag"] for r in rows}

    total = 0
    correct = 0
    mismatches: list[tuple[str, str, str]] = []
    missing: list[str] = []
    for public_id, expected in expected_by_public_id.items():
        if public_id not in got_by_public_id:
            missing.append(public_id)
            continue
        total += 1
        actual = got_by_public_id[public_id]
        if actual == expected:
            correct += 1
        else:
            mismatches.append((public_id, expected, actual))

    accuracy = correct / total if total else 0.0
    print(f"Checked {total}/{len(expected_by_public_id)} seeded assets (missing: {len(missing)})")
    print(f"Rank-1 accuracy: {correct}/{total} = {accuracy:.2%}")

    if mismatches:
        print(f"\n{len(mismatches)} mismatches:")
        for public_id, expected, actual in mismatches:
            print(f"  {public_id}: expected={expected!r} got={actual!r}")

    if missing:
        print(f"\n{len(missing)} seeded files have no clip rank-1 tag yet: {missing}")

    print("\nPer-label accuracy:")
    by_label: dict[str, list[bool]] = {}
    for public_id, expected in expected_by_public_id.items():
        if public_id in got_by_public_id:
            by_label.setdefault(expected, []).append(got_by_public_id[public_id] == expected)
    for label, results in sorted(by_label.items()):
        acc = sum(results) / len(results)
        print(f"  {label:20s} {sum(results)}/{len(results)} = {acc:.0%}")

    if accuracy < 0.6:
        print("\n! accuracy below 0.6 - roadmap says stop and ask the user before retuning labels")


if __name__ == "__main__":
    main()

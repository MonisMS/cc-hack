"""One-time (idempotent) Cloudinary setup for FieldProof.

Probes whether the "AI Content Analysis" add-on is active, then creates/updates
the 3 upload presets the app uses (§3.4 C9 in docs/04-roadmap.md).

Run from backend/:
    uv run python scripts/setup_cloudinary.py

Never imported by the app. Re-run only if the add-on subscription or preset
settings change.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import cloudinary.api  # noqa: E402
import cloudinary.uploader  # noqa: E402

from app.fieldproof import cloudinary_gw  # noqa: E402

SAMPLE_IMAGE = BACKEND_DIR / "samples" / "public" / "Mangrove_plantation.jpg"

COMMON_IMAGE_SETTINGS = {
    "unsigned": True,
    "asset_folder": "fieldproof/originals",
    "use_filename": False,
    "unique_filename": True,
    "overwrite": False,
    "allowed_formats": "jpg,jpeg,png,webp,heic",
    "media_metadata": True,
    "transformation": [{"crop": "limit", "width": 4000, "height": 4000}],
}

VIDEO_SETTINGS = {
    "unsigned": True,
    "asset_folder": "fieldproof/originals",
    "allowed_formats": "mp4,mov",
    "media_metadata": True,
}


def probe_addon() -> bool:
    """Upload a throwaway asset with `detection=` to see if the add-on is active."""
    cloudinary_gw._configure()
    try:
        result = cloudinary.uploader.upload(
            str(SAMPLE_IMAGE),
            public_id="fp_probe",
            overwrite=True,
            detection="coco_v2",
        )
    except Exception as exc:  # noqa: BLE001
        if "subscription" in str(exc).lower():
            print("Add-on probe: no active subscription for AI Content Analysis.")
            return False
        raise
    else:
        print("Add-on probe: succeeded. Full `info` node:")
        print(result.get("info"))
        return True
    finally:
        try:
            cloudinary.api.delete_resources(["fp_probe"])
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: could not delete fp_probe: {exc}")


def upsert_preset(name: str, settings: dict) -> None:
    try:
        cloudinary.api.update_upload_preset(name, **settings)
    except Exception as exc:  # noqa: BLE001
        if "not found" in str(exc).lower() or "can't find" in str(exc).lower():
            cloudinary.api.create_upload_preset(name=name, **settings)
        else:
            raise


def main() -> None:
    cloudinary_gw._configure()
    addon = probe_addon()

    upsert_preset("fp_image_basic", COMMON_IMAGE_SETTINGS)

    fp_image_settings = dict(COMMON_IMAGE_SETTINGS)
    if addon:
        fp_image_settings["detection"] = "coco_v2"
        fp_image_settings["auto_tagging"] = 0.6
    upsert_preset("fp_image", fp_image_settings)

    upsert_preset("fp_video", VIDEO_SETTINGS)

    for name in ("fp_image_basic", "fp_image", "fp_video"):
        preset = cloudinary.api.upload_preset(name)
        print(f"\n{name} settings:")
        print(preset["settings"])

    print(f"\nADDON DETECTION: {'ON' if addon else 'OFF'}")


if __name__ == "__main__":
    main()

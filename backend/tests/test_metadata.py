from datetime import datetime, timedelta, timezone

from app.fieldproof.metadata import (
    dms_to_decimal,
    parse_media_metadata,
    resolve_captured_at,
    resolve_location,
)


def test_dms_south_west_sign():
    assert abs(dms_to_decimal("12 deg 58' 12.3\" N") - (12 + 58 / 60 + 12.3 / 3600)) < 1e-6
    assert dms_to_decimal("12 deg 58' 12.3\" S") < 0
    assert dms_to_decimal("77 deg 35' 0\" W") < 0
    assert dms_to_decimal("77 deg 35' 0\" E") > 0


def test_reject_null_island_and_outside_india():
    lat, lng, src = resolve_location(0, 0, device_lat=28.6, device_lng=77.2)
    assert src == "device"
    assert abs(lat - 28.6) < 1e-6
    lat, lng, src = resolve_location(40.7, -74.0)  # NYC
    assert src == "none"
    assert lat is None


def test_future_date_falls_back_to_upload():
    upload = datetime(2024, 6, 1, tzinfo=timezone.utc)
    future = datetime.now(timezone.utc) + timedelta(days=3)
    dt, src = resolve_captured_at(future, upload)
    assert src == "upload"
    assert dt == upload


def test_before_project_start_falls_back():
    upload = datetime(2024, 6, 1, tzinfo=timezone.utc)
    exif = datetime(2020, 1, 1, tzinfo=timezone.utc)
    dt, src = resolve_captured_at(exif, upload, project_started_on=datetime(2024, 1, 1).date())
    assert src == "upload"


def test_parse_media_metadata_exif_gps():
    upload = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    parsed = parse_media_metadata(
        {
            "image_metadata": {
                "DateTimeOriginal": "2024:05:01 09:30:00",
                "OffsetTimeOriginal": "+05:30",
                "GPSLatitude": "12 deg 58' 12.3\" N",
                "GPSLongitude": "77 deg 35' 0\" E",
            }
        },
        upload_time=upload,
    )
    assert parsed.captured_at_source == "exif"
    assert parsed.location_source == "exif"
    assert parsed.lat is not None and parsed.lat > 0
    assert parsed.lng is not None and parsed.lng > 0

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

KOLKATA = ZoneInfo("Asia/Kolkata")
INDIA_LAT = (6.5, 37.5)
INDIA_LNG = (68.0, 97.5)

_DMS_RE = re.compile(
    r"""
    (?P<deg>-?\d+(?:\.\d+)?)
    \s*(?:deg|°)?\s*
    (?:(?P<min>\d+(?:\.\d+)?)\s*['′]?)?
    \s*
    (?:(?P<sec>\d+(?:\.\d+)?)\s*[\"″]?)?
    \s*(?P<hem>[NnSsEeWw])?
    """,
    re.VERBOSE,
)


@dataclass
class ParsedMeta:
    captured_at: datetime | None
    captured_at_source: str
    lat: float | None
    lng: float | None
    location_source: str
    raw: dict[str, Any]


def dms_to_decimal(s: str) -> float:
    text = (s or "").strip()
    if not text:
        raise ValueError("empty DMS")
    match = _DMS_RE.search(text)
    if not match:
        raise ValueError(f"unrecognised DMS: {s}")
    deg = float(match.group("deg"))
    minutes = float(match.group("min") or 0)
    seconds = float(match.group("sec") or 0)
    hem = (match.group("hem") or "").upper()
    value = abs(deg) + minutes / 60.0 + seconds / 3600.0
    if deg < 0 or hem in {"S", "W"}:
        value = -value
    return value


def _find_key(meta: dict[str, Any], *names: str) -> Any:
    wanted = {n.lower() for n in names}
    if not isinstance(meta, dict):
        return None
    for key, val in meta.items():
        if str(key).lower() in wanted:
            if isinstance(val, dict) and "value" in val:
                return val["value"]
            return val
        if isinstance(val, dict):
            found = _find_key(val, *names)
            if found is not None:
                return found
    return None


def _parse_exif_datetime(value: Any, offset: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z"):
        try:
            dt = datetime.strptime(text.replace("+", "+", 1), fmt)
            break
        except ValueError:
            dt = None
    else:
        return None
    if dt.tzinfo is None:
        tz = KOLKATA
        if offset:
            off = str(offset).strip()
            try:
                sign = 1 if off.startswith("+") else -1
                hh, mm = off.lstrip("+-").split(":")
                tz = timezone(sign * timedelta(hours=int(hh), minutes=int(mm)))
            except (ValueError, AttributeError):
                tz = KOLKATA
        dt = dt.replace(tzinfo=tz)
    return dt


def in_india(lat: float, lng: float) -> bool:
    return INDIA_LAT[0] <= lat <= INDIA_LAT[1] and INDIA_LNG[0] <= lng <= INDIA_LNG[1]


def resolve_location(
    exif_lat: float | None,
    exif_lng: float | None,
    device_lat: float | None = None,
    device_lng: float | None = None,
) -> tuple[float | None, float | None, str]:
    for lat, lng, source in (
        (exif_lat, exif_lng, "exif"),
        (device_lat, device_lng, "device"),
    ):
        if lat is None or lng is None:
            continue
        if (lat, lng) == (0, 0) or (abs(lat) < 1e-6 and abs(lng) < 1e-6):
            continue
        if not in_india(lat, lng):
            continue
        return lat, lng, source
    return None, None, "none"


def resolve_captured_at(
    exif_dt: datetime | None,
    upload_time: datetime,
    project_started_on: date | None = None,
) -> tuple[datetime, str]:
    now = datetime.now(timezone.utc)
    upload_time = _as_utc(upload_time)

    def valid(dt: datetime) -> bool:
        dt = _as_utc(dt)
        if dt > now + timedelta(minutes=5):
            return False
        if project_started_on and dt.date() < project_started_on:
            return False
        return True

    if exif_dt is not None and valid(exif_dt):
        return _as_utc(exif_dt), "exif"
    return upload_time, "upload"


def parse_media_metadata(
    meta: dict[str, Any],
    *,
    upload_time: datetime,
    project_started_on: date | None = None,
    device_lat: float | None = None,
    device_lng: float | None = None,
) -> ParsedMeta:
    raw = meta or {}
    image_meta = raw.get("image_metadata") if isinstance(raw.get("image_metadata"), dict) else raw
    dt_raw = _find_key(image_meta, "DateTimeOriginal", "CreateDate", "DateCreated")
    off_raw = _find_key(image_meta, "OffsetTimeOriginal", "OffsetTime")
    exif_dt = _parse_exif_datetime(dt_raw, off_raw)
    captured_at, captured_src = resolve_captured_at(exif_dt, upload_time, project_started_on)

    lat = _coord(_find_key(image_meta, "GPSLatitude", "Latitude"))
    lng = _coord(_find_key(image_meta, "GPSLongitude", "Longitude"))
    hem_lat = _find_key(image_meta, "GPSLatitudeRef")
    hem_lng = _find_key(image_meta, "GPSLongitudeRef")
    if lat is not None and isinstance(hem_lat, str) and hem_lat.upper().startswith("S") and lat > 0:
        lat = -lat
    if lng is not None and isinstance(hem_lng, str) and hem_lng.upper().startswith("W") and lng > 0:
        lng = -lng

    rlat, rlng, loc_src = resolve_location(lat, lng, device_lat, device_lng)
    return ParsedMeta(
        captured_at=captured_at,
        captured_at_source=captured_src,
        lat=rlat,
        lng=rlng,
        location_source=loc_src,
        raw=raw,
    )


def _coord(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return dms_to_decimal(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KOLKATA).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings

Lat = Field(ge=-90, le=90)
Lng = Field(ge=-180, le=180)
RadiusM = Field(ge=20, le=5000)


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    started_on: date | None = None


class SiteCreate(BaseModel):
    name: str
    lat: float = Lat
    lng: float = Lng
    radius_m: int = Field(default=settings.site_radius_m_default, ge=20, le=5000)


class SitePatch(BaseModel):
    name: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    radius_m: int | None = Field(default=None, ge=20, le=5000)


class AssetRegister(BaseModel):
    project_id: UUID
    cld_public_id: str
    cld_asset_id: str
    cld_version: int
    resource_type: Literal["image", "video"] = "image"
    format: str | None = None
    width: int | None = None
    height: int | None = None
    bytes: int | None = None
    duration_s: float | None = None
    secure_url: str
    device_lat: float | None = Field(default=None, ge=-90, le=90)
    device_lng: float | None = Field(default=None, ge=-180, le=180)
    consent_confirmed: bool = False
    image_metadata: dict | None = None
    detection: dict | None = None


class AssetPatch(BaseModel):
    site_id: UUID | None = None
    captured_at: datetime | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    add_tags: list[str] | None = None
    remove_tags: list[str] | None = None

    @model_validator(mode="after")
    def _lat_lng_together(self) -> "AssetPatch":
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat and lng must be given together")
        return self


class SearchRequest(BaseModel):
    query: str = ""
    project_id: UUID | None = None
    site_id: UUID | None = None
    tag: str | None = None
    status: str | None = None
    limit: int = Field(default=20, ge=1, le=60)


class ComparisonCreate(BaseModel):
    site_id: UUID
    before_asset_id: UUID
    after_asset_id: UUID

    @model_validator(mode="after")
    def _distinct_assets(self) -> "ComparisonCreate":
        if self.before_asset_id == self.after_asset_id:
            raise ValueError("before_asset_id and after_asset_id must differ")
        return self


class ReportCreate(BaseModel):
    project_id: UUID
    date_from: date
    date_to: date
    comparison_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _date_range(self) -> "ReportCreate":
        if self.date_from > self.date_to:
            raise ValueError("date_from must be <= date_to")
        return self

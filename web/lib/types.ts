// Mirrors backend/docs §3.1 (API response shapes). Keep in sync with app/fieldproof/routes.py.

export type Project = {
  id: string;
  name: string;
  description: string | null;
  started_on: string | null; // YYYY-MM-DD
  created_at: string;
  asset_count: number;
  ready_count: number;
  failed_count: number;
  site_count: number;
};

export type Site = {
  id: string;
  project_id: string;
  name: string;
  lat: number;
  lng: number;
  radius_m: number;
  asset_count: number;
};

export type Tag = {
  tag: string;
  source: "clip" | "cld_detection" | "manual";
  score: number | null;
  rank: number | null;
};

export type AssetStatus = "pending" | "processing" | "ready" | "failed";

export type AssetCard = {
  id: string;
  project_id: string;
  site_id: string | null;
  site_name: string | null;
  status: AssetStatus;
  resource_type: "image" | "video";
  thumb_url: string;
  captured_at: string | null;
  tags: Tag[];
};

export type AssetDetail = AssetCard & {
  cld_public_id: string;
  cld_version: number;
  secure_url: string;
  compare_url: string;
  width: number | null;
  height: number | null;
  captured_at_source: "exif" | "upload" | "manual" | null;
  lat_r: number | null;
  lng_r: number | null;
  location_source: "exif" | "device" | "manual" | "none" | null;
  consent_confirmed: boolean;
  error: string | null;
};

export type SearchHit = {
  asset: AssetCard;
  score: number;
};

export type PairSuggestion = {
  before: AssetCard;
  after: AssetCard;
  image_similarity: number;
  framing_warning: boolean;
  days_apart: number;
};

export type ComparisonStatus = "pending" | "processing" | "ready" | "failed";

export type Comparison = {
  id: string;
  site_id: string;
  site_name: string;
  status: ComparisonStatus;
  before: AssetCard;
  after: AssetCard;
  before_compare_url: string;
  after_compare_url: string;
  before_mask_url: string | null;
  after_mask_url: string | null;
  image_similarity: number | null;
  framing_warning: boolean | null;
  before_green_pct_rounded: number | null;
  after_green_pct_rounded: number | null;
  delta_green_pct_rounded: number | null;
  days_apart: number | null;
  description: string | null;
  description_model: string | null;
  created_at: string;
};

export type ReportStatus = "pending" | "processing" | "ready" | "failed";

export type ReportSummary = {
  headline: string;
  paragraphs: string[];
  highlights: string[];
};

export type Report = {
  id: string;
  project_id: string;
  status: ReportStatus;
  date_from: string | null;
  date_to: string | null;
  metrics: Record<string, unknown>;
  summary: ReportSummary | null;
  summary_model: string | null;
  items: ReportItem[];
  created_at: string;
};

export type ReportItem = {
  position: number;
  kind: "asset" | "comparison";
  section: string | null;
  asset: AssetCard | null;
  comparison: Comparison | null;
};

export type KitItemKind = "social_square" | "social_story" | "collage";

export type KitItem = {
  kind: KitItemKind;
  url: string;
  source_asset_ids: string[];
  transformation: string;
};

export type LineageRecord = {
  id: string;
  entity_type: "asset" | "comparison" | "report" | "kit";
  entity_id: string;
  output_kind: string;
  output_ref: string | null;
  source_asset_ids: string[];
  source_public_ids: string[];
  source_versions: number[];
  tool: string | null;
  transformation: string | null;
  model: string | null;
  params: Record<string, unknown>;
  created_at: string;
};

export type ApiErrorEnvelope = {
  error: {
    code: string;
    message: string;
    details: unknown;
  };
};

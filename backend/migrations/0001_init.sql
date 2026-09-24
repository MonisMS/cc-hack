-- FieldProof initial schema (LLD §2). Direct Neon connection only.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    description text,
    started_on date,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sites (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    name text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    radius_m integer NOT NULL DEFAULT 200,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sites_project_id_idx ON sites (project_id);

CREATE TABLE IF NOT EXISTS assets (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects (id),
    site_id uuid REFERENCES sites (id),
    cld_public_id text NOT NULL UNIQUE,
    cld_asset_id text NOT NULL UNIQUE,
    cld_version integer NOT NULL,
    resource_type text NOT NULL CHECK (resource_type IN ('image', 'video')),
    format text,
    width integer,
    height integer,
    bytes bigint,
    duration_s real,
    secure_url text NOT NULL,
    captured_at timestamptz,
    captured_at_source text CHECK (captured_at_source IN ('exif', 'upload', 'manual')),
    lat double precision,
    lng double precision,
    location_source text CHECK (location_source IN ('exif', 'device', 'manual', 'none')),
    consent_confirmed boolean NOT NULL DEFAULT false,
    status text NOT NULL CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    error text,
    media_metadata jsonb,
    cld_detection jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS assets_project_id_idx ON assets (project_id);
CREATE INDEX IF NOT EXISTS assets_site_id_idx ON assets (site_id);
CREATE INDEX IF NOT EXISTS assets_captured_at_idx ON assets (captured_at);
CREATE INDEX IF NOT EXISTS assets_status_idx ON assets (status);

CREATE TABLE IF NOT EXISTS asset_embeddings (
    asset_id uuid NOT NULL REFERENCES assets (id) ON DELETE CASCADE,
    frame_s real NOT NULL DEFAULT 0,
    embedding vector(512) NOT NULL,
    model text NOT NULL,
    PRIMARY KEY (asset_id, frame_s)
);

CREATE TABLE IF NOT EXISTS asset_tags (
    asset_id uuid NOT NULL REFERENCES assets (id) ON DELETE CASCADE,
    tag text NOT NULL,
    source text NOT NULL CHECK (source IN ('clip', 'cld_detection', 'manual')),
    score real,
    rank smallint,
    PRIMARY KEY (asset_id, tag, source)
);
CREATE INDEX IF NOT EXISTS asset_tags_tag_idx ON asset_tags (tag);

CREATE TABLE IF NOT EXISTS comparisons (
    id uuid PRIMARY KEY,
    site_id uuid NOT NULL REFERENCES sites (id),
    before_asset_id uuid NOT NULL REFERENCES assets (id),
    after_asset_id uuid NOT NULL REFERENCES assets (id),
    image_similarity real,
    framing_warning boolean,
    before_green_pct real,
    after_green_pct real,
    delta_green_pct_rounded smallint,
    before_mask_public_id text,
    after_mask_public_id text,
    description text,
    description_model text,
    status text NOT NULL CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (before_asset_id <> after_asset_id)
);
CREATE INDEX IF NOT EXISTS comparisons_site_id_idx ON comparisons (site_id);

CREATE TABLE IF NOT EXISTS reports (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects (id),
    date_from date,
    date_to date,
    metrics jsonb,
    summary jsonb,
    summary_model text,
    status text NOT NULL CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_items (
    report_id uuid NOT NULL REFERENCES reports (id) ON DELETE CASCADE,
    position smallint NOT NULL,
    kind text NOT NULL CHECK (kind IN ('asset', 'comparison')),
    asset_id uuid REFERENCES assets (id),
    comparison_id uuid REFERENCES comparisons (id),
    section text,
    PRIMARY KEY (report_id, position)
);

CREATE TABLE IF NOT EXISTS lineage (
    id uuid PRIMARY KEY,
    entity_type text NOT NULL,
    entity_id uuid NOT NULL,
    output_kind text NOT NULL,
    output_ref text,
    source_asset_ids uuid[],
    source_public_ids text[],
    source_versions integer[],
    tool text,
    transformation text,
    model text,
    params jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS lineage_entity_idx ON lineage (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS jobs (
    id bigserial PRIMARY KEY,
    kind text NOT NULL,
    payload jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed')),
    attempts smallint NOT NULL DEFAULT 0,
    max_attempts smallint NOT NULL DEFAULT 5,
    run_after timestamptz NOT NULL DEFAULT now(),
    locked_at timestamptz,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_status_run_after_idx ON jobs (status, run_after);

CREATE TABLE IF NOT EXISTS llm_cache (
    key text PRIMARY KEY,
    model text,
    response jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

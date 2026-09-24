# 03 — Project Structure: FieldProof (monorepo)

_Builds on [02-lld.md](02-lld.md). Legend: ✅ exists in the repo today (24 Sep 2026) · ⏳ planned (created during the build). Tags: [VERIFIED: …] · [UNVERIFIED] · [ASSUMPTION]. 🟡 = new choice, listed in §7 for approval._

---

## 1. Top-level layout

```
cc-hack/                         ✅ monorepo root (git managed by the team, not by tooling)
├── .gitignore                   ✅ secrets, .venv, models/, node_modules, sample photos
├── README.md                    ⏳ what it is, quick start, links to docs/
├── .github/
│   └── workflows/
│       └── ci.yml               ⏳ lint + tests on push (backend pytest, web lint + build)
├── docs/                        ✅ planning docs (this folder)
├── backend/                     ✅ Python 3.12 · FastAPI · worker · CLIP  (Dev A + Dev B)
└── web/                         ✅ Next.js 16 · next-cloudinary · shadcn/ui (Dev B lead)
```

PS1 (Scout) will later live **inside the same backend and web apps** as a second feature package (`backend/app/scout/`, `web/app/scout/…`), reusing `backend/app/core/` and `web/components/`. [R: approved monorepo decision, 00-research §6.1]

---

## 2. Backend tree (`backend/`)

```
backend/
├── pyproject.toml               ✅ uv project, Python ≥3.12, dependencies
├── uv.lock                      ✅ exact versions; commit it so both laptops match
├── .python-version              ✅ 3.12
├── .env.example                 ✅ env var names (copy to .env)
├── .env                         —  local secrets, git-ignored, never committed
├── models/                      —  CLIP ONNX cache (~580 MB), git-ignored
├── migrations/                  ⏳ numbered SQL files (LLD D2)
│   ├── 0001_init.sql            ⏳ CREATE EXTENSION vector + all tables (LLD §2)
│   └── 0002_….sql               ⏳ later changes, never edit an applied file
├── scripts/
│   ├── clip_benchmark.py        ✅ speed/accuracy/threshold benchmark (commits results)
│   ├── migrate.py               ⏳ applies migrations/*.sql in order over the DIRECT DB URL
│   ├── download_models.py       ⏳ pre-downloads both CLIP models into models/
│   ├── setup_cloudinary.py      ⏳ creates the structured metadata fields (LLD §4.3); prints preset checklist
│   └── seed_demo.py             ⏳ creates the demo project/sites and registers demo uploads
├── samples/
│   ├── public/                  —  Wikimedia benchmark images (downloaded, git-ignored except CREDITS.md)
│   └── mine/                    ✅ your own test photos (git-ignored except .gitkeep)
├── bench-results/               ✅ benchmark JSON per laptop (committed, so the team can compare)
├── tests/
│   ├── test_health.py           ✅
│   ├── test_metadata.py         ⏳ DMS→decimal, date/location resolution rules
│   ├── test_change.py           ⏳ green_cover on synthetic images
│   ├── test_llm_placeholders.py ⏳ number-guard validator
│   ├── test_sites.py            ⏳ haversine assignment
│   └── test_search.py           ⏳ integration: benchmark queries return expected samples
└── app/
    ├── __init__.py              ✅
    ├── main.py                  ✅ FastAPI app, CORS, /health; ⏳ mount routers
    ├── worker.py                ⏳ `python -m app.worker`, the job poll loop
    ├── core/                    ✅ SHARED with PS1: no FieldProof imports allowed here
    │   ├── __init__.py          ✅
    │   ├── config.py            ✅ Settings (pydantic-settings), model constants
    │   ├── db.py                ✅ engine + health check; ⏳ get_session()
    │   ├── jobs.py              ⏳ enqueue / claim (SKIP LOCKED) / complete / fail
    │   ├── llm.py               ⏳ LiteLLM router, cache, generate_json, placeholder guard
    │   └── errors.py            ⏳ ApiError + exception handlers
    └── fieldproof/              ✅ PS2 feature package
        ├── __init__.py          ✅
        ├── models.py            ⏳ SQLAlchemy ORM (LLD §2)
        ├── schemas.py           ⏳ Pydantic request/response models (LLD §3)
        ├── routes.py            ⏳ APIRouter for /api/* (LLD §3)
        ├── cloudinary_gw.py     ⏳ the only module that calls Cloudinary
        ├── transforms.py        ⏳ the fixed named transformations (LLD §4.2)
        ├── embeddings.py        ⏳ CLIP load-once, embed, zero-shot labels_v1
        ├── metadata.py          ⏳ EXIF/GPS/date parsing + validation
        ├── sites.py             ⏳ site assignment
        ├── change.py            ⏳ green_cover v1, framing check, mask image
        ├── search.py            ⏳ filtered cosine search (LLD §5.4)
        ├── reports.py           ⏳ metrics SQL, evidence selection, campaign kit
        ├── lineage.py           ⏳ record / query lineage
        └── pipelines.py         ⏳ job handlers: analyze_asset, build_comparison, generate_report
```

**Dependency rule:** `app/core/*` must never import from `app/fieldproof/*` or `app/scout/*`. Feature packages import from `core`, never from each other. 🟡 [ASSUMPTION: this keeps core reusable for PS1]

**Dependencies still to add** (installed during the build, not now):
- `cloudinary`: 1.46.2 confirmed working [SDK check in 02-lld];
- `litellm`, for the LLM router [R§2.2];
- `ruff`, for linting (🟡 §7).

---

## 3. Frontend tree (`web/`)

```
web/
├── package.json                 ✅ Next 16.3.6, React 19.2.8, Tailwind v4, ESLint (pnpm)
├── pnpm-workspace.yaml          ✅ created by create-next-app
├── pnpm-lock.yaml               ⏳ created by the first successful `pnpm install`; commit it
│                                   (24 Sep: not present, because the 23 Sep install did not persist; re-run `pnpm install`)
├── next.config.ts               ✅ ⏳ add images.remotePatterns for res.cloudinary.com if next/image is used
├── tsconfig.json                ✅ path alias @/*
├── eslint.config.mjs            ✅
├── postcss.config.mjs           ✅
├── .env.example                 ⏳ public env var names (copy to .env.local)
├── .env.local                   —  git-ignored
├── components.json              ⏳ created by `shadcn init`
├── app/                         ✅ App Router
│   ├── layout.tsx               ✅ ⏳ wrap in AppShell
│   ├── globals.css              ✅ ⏳ + print styles (@media print)
│   ├── page.tsx                 ✅ ⏳ dashboard: projects + health + credit meter
│   ├── projects/[id]/
│   │   ├── page.tsx             ⏳ project overview (counts, recent assets)
│   │   ├── upload/page.tsx      ⏳ UploadPanel (two buttons: photos / videos)
│   │   ├── library/page.tsx     ⏳ AssetGrid + filters
│   │   ├── map/page.tsx         ⏳ SiteMap (client-only)
│   │   └── timeline/page.tsx    ⏳ Timeline
│   ├── assets/[id]/page.tsx     ⏳ detail: tags by source, date/location source, lineage
│   ├── search/page.tsx          ⏳ SearchBar + Filters + results
│   ├── sites/[id]/compare/page.tsx  ⏳ pair suggestions → create comparison
│   ├── comparisons/[id]/page.tsx    ⏳ CompareSlider + mask toggle + description
│   ├── reports/[id]/page.tsx        ⏳ ReportView + CampaignKit
│   ├── reports/[id]/print/page.tsx  ⏳ print layout → browser "Save as PDF"
│   └── admin/usage/page.tsx         ⏳ UsageMeter (Cloudinary credits)
├── components/
│   ├── ui/                      ⏳ shadcn-generated primitives (button, card, sheet, table, …)
│   ├── app-shell.tsx            ⏳ sidebar layout
│   ├── asset-card.tsx · asset-grid.tsx · tag-chips.tsx · status-badge.tsx    ⏳
│   ├── upload-panel.tsx         ⏳ CldUploadWidget → POST /api/assets/register
│   ├── site-map.tsx             ⏳ "use client" + next/dynamic(ssr:false) Leaflet
│   ├── timeline.tsx · search-filters.tsx                                       ⏳
│   ├── compare-slider.tsx       ⏳ "use client" react-compare-slider
│   ├── lineage-panel.tsx        ⏳ shadcn Sheet
│   ├── report-view.tsx · campaign-kit.tsx · usage-meter.tsx                    ⏳
├── lib/
│   ├── api.ts                   ⏳ typed fetch wrapper + usePoll hook (LLD D9)
│   ├── types.ts                 ⏳ hand-written API types mirroring LLD §3 (LLD D10)
│   └── transforms.ts            ⏳ same named transforms as backend/transforms.py
└── public/                      ✅ static assets (logo, demo placeholder images)
```

**Dependencies still to add:**
- `next-cloudinary` 6.19.x [R§1.8];
- `leaflet` + `react-leaflet` 5 [R§3];
- `react-compare-slider` 4 [R§3];
- shadcn/ui via its CLI [R§3].

---

## 4. Naming conventions 🟡

| Thing | Convention | Example |
|---|---|---|
| Python modules / functions / variables | `snake_case` | `cloudinary_gw.py`, `resolve_location()` |
| Python classes / Pydantic models | `PascalCase` | `AssetDetail`, `SearchRequest` |
| Python constants / env vars | `UPPER_SNAKE_CASE` | `EMBED_DIM`, `DATABASE_URL` |
| DB tables | `snake_case`, plural | `assets`, `asset_tags` |
| DB columns | `snake_case`; Cloudinary IDs prefixed `cld_` | `cld_public_id` |
| API paths | lowercase, plural nouns, kebab-case for multiword | `/api/sites/{id}/pair-suggestions` |
| JSON fields in API | `snake_case` (same as Python; no conversion layer) | `captured_at` |
| React component files | `kebab-case.tsx`; component names `PascalCase` | `site-map.tsx` → `SiteMap` |
| Next.js route folders | lowercase, `[param]` for dynamic | `app/reports/[id]/print` |
| Cloudinary asset folders | `fieldproof/originals`, `fieldproof/derived/masks` | — |
| Cloudinary upload presets | `fp_<kind>` | `fp_image`, `fp_image_basic`, `fp_video` |
| Cloudinary structured metadata IDs | `fp_<name>` | `fp_project`, `fp_site`, `fp_phase` |
| Job kinds | `verb_noun` | `analyze_asset`, `build_comparison` |
| Migration files | `NNNN_short_description.sql` | `0001_init.sql` |
| Benchmark results | `<hostname>-<YYYYMMDD-HHMMSS>.json` (automatic) | ✅ existing |

---

## 5. Environment variables (names only, no values)

### 5.1 Backend: `backend/.env` (read by `app/core/config.py` via pydantic-settings; names are case-insensitive field matches)
| Name | Required | Purpose | Status |
|---|---|---|---|
| `DATABASE_URL` | ✅ | Neon **direct** connection string with the `postgresql+psycopg://` prefix and `sslmode=require` [R§4] | ✅ in `.env.example` |
| `CLOUDINARY_URL` | ✅ | `cloudinary://API_KEY:API_SECRET@CLOUD_NAME`, backend only | ✅ in `.env.example` |
| `GEMINI_API_KEY` | ✅ | LLM chain step 1 [R§2.2] | ✅ in `.env.example` |
| `GROQ_API_KEY` | ✅ | LLM chain step 2 (+ optional vision) | ✅ in `.env.example` |
| `CEREBRAS_API_KEY` | ✅ | LLM chain step 3 | ✅ in `.env.example` |
| `HF_HUB_OFFLINE` | ✅ | `1` after models are downloaded [R§2.1] | ✅ in `.env.example` |
| `GEMINI_MODEL` | ✅ | Exact Gemini model ID (UNVERIFIED string, copy from Google docs) | ⏳ add |
| `CORS_ORIGINS` | ✅ | JSON list, e.g. local web URL + Vercel URL | ⏳ add (default exists in code) |
| `MODELS_DIR` | — | Override the CLIP cache path (default `backend/models`) | ⏳ add (default exists in code) |
| `CLOUDINARY_IMAGE_PRESET` | — | `fp_image` or `fp_image_basic` (LLD §9) | ⏳ add |
| `ENABLE_G_AUTO` | — | `true`/`false` (LLD §9) | ⏳ add |
| `ENABLE_BLUR_FACES` | — | `true`/`false` | ⏳ add |
| `ENABLE_VISION_DESCRIPTIONS` | — | default `false` | ⏳ add |
| `CREDIT_GUARD_PERCENT` | — | default `80` | ⏳ add |
| `FRAMING_SIM_THRESHOLD` | — | default `0.80` | ⏳ add |
| `GREEN_EXG_THRESHOLD` | — | default `0.10` | ⏳ add |
| `SITE_RADIUS_M_DEFAULT` | — | default `200` | ⏳ add |
| `DEMO_MODE` | — | `true` = read-only, cached results only | ⏳ add |

### 5.2 Frontend: `web/.env.local`
- Anything prefixed `NEXT_PUBLIC_` is exposed to the browser [VERIFIED: https://nextjs.org/docs/app/guides/environment-variables].
- **So no secrets here.**

| Name | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | FastAPI base URL (local `http://localhost:8000`, prod HTTPS URL) |
| `NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME` | ✅ | Used by next-cloudinary [R§1.8] |
| `NEXT_PUBLIC_CLOUDINARY_IMAGE_PRESET` | ✅ | `fp_image` (or `fp_image_basic`) |
| `NEXT_PUBLIC_CLOUDINARY_VIDEO_PRESET` | ✅ | `fp_video` |
| `NEXT_PUBLIC_CLOUDINARY_API_KEY` | ? | Only if next-cloudinary's widget needs it for unsigned uploads [UNVERIFIED, 02-lld §13 item 7]. The API **key** is not secret; the **secret** is. [ASSUMPTION based on Cloudinary's key/secret split] |

`CLOUDINARY_API_SECRET` is **never** set in `web/`. The frontend does unsigned uploads only [LLD §4.1].

---

## 6. Local setup (both laptops)

### 6.1 Prerequisites (one time)
1. **OS:** Linux/macOS, or **WSL2 on Windows**. Keep the repo in the Linux home folder (`~/cc-hack`), not `/mnt/c` [ps2-edge-cases #1].
2. **Node.js ≥ 20.9** (Next 16 requirement) [VERIFIED: https://nextjs.org/blog/next-16]. This machine has v22.23.2.
3. **pnpm**. This machine has 10.34.5. Install with `npm i -g pnpm`.
4. **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`. uv downloads Python 3.12 itself (pinned in `.python-version`).
5. **Accounts:**
   - Cloudinary (free);
   - Neon (free);
   - Google AI Studio (Gemini key);
   - Groq;
   - Cerebras.

### 6.2 Backend
```bash
cd ~/cc-hack/backend
uv sync                                   # installs exact versions from uv.lock
cp .env.example .env                      # then fill values (never commit .env)
uv run python scripts/clip_benchmark.py   # first run downloads ~580 MB of models (~17 min here)
# after the download: set HF_HUB_OFFLINE=1 in .env
uv run python scripts/migrate.py          # ⏳ creates tables (DIRECT Neon URL)
uv run uvicorn app.main:app --reload --port 8000     # API → http://localhost:8000/health
uv run python -m app.worker               # ⏳ second terminal: job worker
uv run pytest                             # tests
```

### 6.3 Frontend
```bash
cd ~/cc-hack/web
pnpm install
cp .env.example .env.local                # ⏳ file to be created; fill public values
pnpm dev                                  # → http://localhost:3000
pnpm lint
```

### 6.4 Cloudinary Console (one time, Dev B)
1. **Add-ons:** register the free tier of **Cloudinary AI Content Analysis** (for `coco_v2` detection). Record every add-on quota in `docs/06-risks…` [R§1.3].
2. **Upload presets:** create `fp_image`, `fp_image_basic` and `fp_video` exactly as in LLD §4.1, all **Unsigned**.
3. **Settings:** confirm the folder mode is dynamic [R§1.4].
4. Run `uv run python scripts/setup_cloudinary.py` (⏳) to create the structured metadata fields (optional D12).
5. **Test URLs:**
   - one `c_fill,g_auto` URL and one `e_blur_faces` URL, to confirm Free-plan support;
   - one `COLLAGE` URL;
   - record the results [02-lld §13].

### 6.5 Neon (one time, Dev A)
1. Create a project and pick the region **closest to India** that's offered. The list of available regions is [UNVERIFIED]; check it in the Neon console.
2. Copy the **direct** (non-pooler) connection string into `DATABASE_URL` with the `postgresql+psycopg://` prefix [R§4].
3. `uv run python scripts/migrate.py` runs `CREATE EXTENSION vector` first [R§4].
4. Check: `curl localhost:8000/health` shows `"database": {"status": "ok", "pgvector": true}`.

### 6.6 Everyday commands (cheat sheet)
| Task | Command (from folder) |
|---|---|
| Run API | `uv run uvicorn app.main:app --reload --port 8000` (backend/) |
| Run worker | `uv run python -m app.worker` (backend/) |
| Run web | `pnpm dev` (web/) |
| Backend tests | `uv run pytest` (backend/) |
| Web lint / build | `pnpm lint` / `pnpm build` (web/) |
| Add Python dependency | `uv add <pkg>` (backend/), then commit `pyproject.toml` + `uv.lock` |
| Add web dependency | `pnpm add <pkg>` (web/), then commit `package.json` + `pnpm-lock.yaml` |
| Re-run CLIP benchmark offline | `uv run python scripts/clip_benchmark.py --offline` (backend/) |

---

## 7. ✅ Choices introduced in this doc (team approved all on 24 Sep 2026)
| # | Choice | Alternatives |
|---|---|---|
| S1 | `app/core` must not import feature packages (enforced by review) | No rule; separate `core` Python package |
| S2 | Naming conventions in §4 (snake_case JSON, kebab-case component files) | camelCase JSON with a conversion layer; PascalCase component files |
| S3 | Add `ruff` for Python lint/format | black + flake8; no Python linter |
| S4 | Helper scripts in `backend/scripts/` (migrate, download_models, setup_cloudinary, seed_demo) | Makefile/justfile at root; npm scripts |
| S5 | GitHub Actions `ci.yml` (pytest + pnpm lint/build) | No CI; pre-commit hooks only |

## 8. [UNVERIFIED] items introduced in this doc
1. The Neon regions available and which is closest to India.
2. Whether `NEXT_PUBLIC_CLOUDINARY_API_KEY` is needed for unsigned widget uploads (repeated from 02-lld).

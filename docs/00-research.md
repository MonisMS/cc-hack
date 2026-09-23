# 00 — Research: FieldProof (PS2, Cloudinary)

_Research date: 23 Sep 2026. Every claim that matters is tagged:_
- **[VERIFIED: url]**: confirmed on an official page (docs, pricing, changelog, package registry) or by our own benchmark run.
- **[UNVERIFIED]**: could not be confirmed. The entry says how to check it.
- **[ASSUMPTION]**: a design judgement without hard evidence. The entry says why.

_Decisions the team has already made are marked 🔒 **LOCKED**. New stack choices are marked 🟡 **PROPOSED**; they need team approval before anyone builds on them._

---

## 0. Timeline conflict (must resolve first)

| Source | Online round / submission | Offline round |
|---|---|---|
| Team brief (planning prompt) | 3 Oct 2026 | 11 Oct 2026 |
| Organisers' email via HackCulture (pasted by team, 23 Sep) | **Submission deadline 30 Sep 2026** ("9 days to build your prototype") | Not mentioned |

- **[UNVERIFIED]** Which date is binding. Check: ask in the official WhatsApp group or the HackCulture event page.
- **[ASSUMPTION]** Until confirmed, all planning treats **30 Sep** as the hard deadline for a complete, deployed submission, and 1–11 Oct as polish time for the offline round. Planning for the earlier date is the safe choice.

---

## 1. Cloudinary (required by the problem statement)

### 1.1 Free plan limits
| Fact | Tag |
|---|---|
| 25 monthly credits, 3 users, 1 account, $0, no credit card | [VERIFIED: https://cloudinary.com/pricing] |
| 1 credit = 1,000 transformations **or** 1 GB managed storage **or** 1 GB image bandwidth | [VERIFIED: https://cloudinary.com/pricing] |
| On Free, 1 credit = 1 GB of **video** bandwidth. Paid plans get 2 GB. | [VERIFIED: https://cloudinary.com/documentation/billing_and_plans] |
| 1 credit ≈ 500 s of SD or 250 s of HD video processing | [VERIFIED: https://cloudinary.com/pricing/compare-plans] |
| Max file sizes: image 10 MB, video 100 MB, raw 10 MB. Max 25 MP per image, 50 MP for multi-frame. | [VERIFIED: https://cloudinary.com/pricing/compare-plans] |
| Admin API: 500 requests/hour on Free. The Upload API is not rate-limited. | [VERIFIED: https://cloudinary.com/pricing/compare-plans], [VERIFIED: https://cloudinary.com/documentation/admin_api] |
| Transformations and bandwidth count over a **rolling 30-day window**. Storage is the current total. | [VERIFIED: https://cloudinary.com/documentation/developer_onboarding_faq_credits] |
| Going over credits: warning emails, then upgrade prompts, then the account is "eventually automatically disabled" | [VERIFIED: https://cloudinary.com/documentation/billing_and_plans] |
| Add-on quotas are a **hard limit**. The add-on stops working until its quota renews. | [VERIFIED: https://cloudinary.com/documentation/billing_and_plans] |

### 1.2 Transformation cost rules (credit budgeting)
| Fact | Tag |
|---|---|
| Each upload = 1 transformation. A chained image transformation = 1. | [VERIFIED: https://cloudinary.com/documentation/transformation_counts] |
| Video (h264/h265/vp9) per second: SD = 2, HD = 4, 4K = 8 transformations. Part-seconds round up. | [VERIFIED: same] |
| Video add-ons per second: video `g_auto` +10, video preview +2, AI Video Analysis +20 | [VERIFIED: same] |
| Background removal = 75. gen_fill / gen_remove / gen_recolor = 50. gen_replace = 120. gen_background_replace = 230. gen_restore / enhance = 100. | [VERIFIED: same] |
| On Explicit calls, `media_metadata`, `phash`, `colors` and `faces` each count as a transformation | [VERIFIED: same] |
| Generative AI and background removal **allowed on Free?** No page states a restriction. | [UNVERIFIED]. Check: try one `e_gen_remove` URL on our account. |

### 1.3 AI add-ons
| Fact | Tag |
|---|---|
| "Most add-ons provide a Free plan with a small monthly quota … you can register for these, even when on a Free Cloudinary plan" | [VERIFIED: https://cloudinary.com/documentation/cloudinary_add_ons] |
| Add-ons are billed separately and do **not** use base credits | [VERIFIED: https://cloudinary.com/documentation/developer_onboarding_faq_credits] |
| Relevant add-ons: Google Auto Tagging, Amazon Rekognition Auto Tagging, Imagga Auto Tagging, Cloudinary AI Content Analysis, Cloudinary AI Vision, Google Automatic Video Tagging, Google AI Video Transcription, Microsoft Azure Video Indexer | [VERIFIED: https://cloudinary.com/documentation/cloudinary_add_ons] |
| **Free monthly units for each add-on** are not on any public doc page. They are only visible in Console → Add-ons (login required). | [UNVERIFIED]. Check: log in, open each add-on, record its Free quota. |

### 1.4 Upload API behaviour (shapes the upload design)
| Fact | Tag |
|---|---|
| **Unsigned** uploads accept only: upload_preset, public_id, public_id_prefix, folder, asset_folder, tags, context, metadata, face_coordinates, custom_coordinates, regions, source, filename_override, manifest_transformation, manifest_json, template, template_vars. Every other parameter must be set **inside the upload preset**. | [VERIFIED: https://cloudinary.com/documentation/image_upload_api_reference] |
| For unsigned uploads the preset wins for single-value parameters. tags, context and metadata are merged. `overwrite` is always false. | [VERIFIED: same] |
| `media_metadata=true` returns IPTC, XMP and EXIF (`image_metadata` / `exif` are deprecated). The response field is still named **`image_metadata`**. | [VERIFIED: same] |
| `categorization`: google_tagging, google_video_tagging, imagga_tagging, aws_rek_tagging. `auto_tagging`: a confidence threshold from 0.0 to 1.0. | [VERIFIED: same] |
| `detection`: `<model>_[<version>]` (e.g. `coco_v2`), plus captioning, iqa, watermark-detection. Models: coco, lvis, unidet, cld-fashion, human-anatomy, cld-text, image-type, captioning, iqa, … | [VERIFIED: https://cloudinary.com/documentation/cloudinary_ai_content_analysis_addon] |
| `eager` (pipe-separated), `eager_async` (default false), `eager_notification_url`, `notification_url` | [VERIFIED: https://cloudinary.com/documentation/image_upload_api_reference] |
| An incoming transformation can be set in a preset. **Never put `f_auto` in an incoming transformation.** | [VERIFIED: https://cloudinary.com/documentation/eager_and_incoming_transformations] |
| Chunked upload is required above 100 MB | [VERIFIED: https://cloudinary.com/documentation/image_upload_api_reference] |
| Accounts created after 4 June 2024 use **dynamic folder mode** | [VERIFIED: https://cloudinary.com/documentation/folder_modes] |

### 1.5 AI Vision add-on (LLM-style image understanding)
| Fact | Tag |
|---|---|
| `POST https://api.cloudinary.com/v2/analysis/<CLOUD_NAME>/analyze/ai_vision_tagging` takes a source (uri or asset_id) and tag_definitions (max 10) | [VERIFIED: https://cloudinary.com/documentation/cloudinary_ai_vision_addon] |
| `…/analyze/ai_vision_general` takes a source and prompts (max 10) for free-form questions | [VERIFIED: same] |
| Billed by tokens. Each response includes a `limits` node. The image does not need to be stored in Cloudinary. | [VERIFIED: same] |
| Free quota | [UNVERIFIED]. Check in Console → Add-ons. |

### 1.6 Transformations we plan to use
| Fact | Tag |
|---|---|
| `g_auto` (content-aware crop) works for images and videos, not animated images | [VERIFIED: https://cloudinary.com/documentation/transformation_reference] |
| `g_auto` available on the **Free** plan | [UNVERIFIED]. No restriction is stated. Check: request one `c_fill,g_auto` URL. |
| `e_blur_faces` and `e_pixelate_faces` (images only) | [VERIFIED: https://cloudinary.com/documentation/transformation_reference] |
| `so_<time>` picks the video frame for a thumbnail | [VERIFIED: same] |
| Text overlays: a comma must be `%252C` and a slash `%252F` (double-encoded) | [VERIFIED: https://cloudinary.com/documentation/image_text_layers] |
| In an overlay public ID, `/` becomes `:` (`sites/a` → `sites:a`) | [VERIFIED: https://cloudinary.com/documentation/layers] |
| Long videos (over 30 min progressive) process asynchronously and return 423 until ready | [VERIFIED: https://cloudinary.com/documentation/video_manipulation_and_delivery] |
| Free-plan size limit for synchronous (on-the-fly) video transformation | [UNVERIFIED]. No official page found. Check: transform a 60 MB clip on the fly. |

### 1.7 Search, metadata, webhooks
| Fact | Tag |
|---|---|
| Search API Tier 1 is automatic for all environments. Tier 2 (image_metadata, location, colors, taken_at, …) is **Advanced plans and above only**. | [VERIFIED: https://cloudinary.com/documentation/search_method] |
| Search calls count against the 500/hour Admin API limit | [VERIFIED: https://cloudinary.com/documentation/admin_api] |
| `GET /usage` returns credit, storage and bandwidth usage | [VERIFIED: same] |
| Structured metadata types: string, integer, date, enum, set. Max 100 fields per environment. Set on upload with `metadata=ext_id=value\|…` | [VERIFIED: https://cloudinary.com/documentation/structured_metadata], [VERIFIED: https://cloudinary.com/documentation/image_upload_api_reference] |
| **DAM visual / natural-language search** is Assets Enterprise only, and not in the Free plan | [VERIFIED: https://cloudinary.com/documentation/dam_visual_search] |
| Webhooks: 20 s timeout. On a non-200 response, 3 retries at 3, 6 and 9 minutes. Signed with X-Cld-Signature / X-Cld-Timestamp. | [VERIFIED: https://cloudinary.com/documentation/notifications] |

### 1.8 Cloudinary tooling
| Fact | Tag |
|---|---|
| `next-cloudinary` 6.19.3 (17 Sep 2026). Peer dependencies include Next ^16 and React ^19. | [VERIFIED: https://registry.npmjs.org/next-cloudinary] |
| Components: CldImage, CldOgImage, CldUploadButton, CldUploadWidget, CldVideoPlayer, and the `getCldImageUrl` helper | [VERIFIED: https://next.cloudinary.dev/installation] |
| Env vars: NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME, NEXT_PUBLIC_CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET | [VERIFIED: https://next.cloudinary.dev/installation] |
| Official MCP servers: Asset Management, Environment Config, Structured Metadata, Analysis, MediaFlows. Some features need paid plans. | [VERIFIED: https://github.com/cloudinary/mcp-servers] |
| Hackathon page: free account, starter kits, Skills Pack. **No upfront credits.** Only a "credits boost" for winners and honourable mentions. | [VERIFIED: https://cloudinary.com/pages/hackathons/] |

### 1.9 What this means for the design
1. **Semantic search must be built by us** (CLIP + pgvector), because Cloudinary's visual search is Enterprise-only [VERIFIED above].
2. **Location and date filtering must happen in our own database.** Cloudinary's Tier 2 search is not available to us [VERIFIED above].
3. **Every AI and metadata option goes inside the unsigned upload preset** [VERIFIED above].
4. **Our database is the source of truth.** The Admin API is limited to 500/hour [VERIFIED above].
5. **Credit budget:** keep a fixed set of named transformations, short SD video only, and generative AI at most once for demo polish. [ASSUMPTION: 25 credits is enough for about 200 images and 5 short clips. Estimated from the VERIFIED cost rules; measured usage to be checked daily.]

---

## 2. AI / ML

### 2.1 Local embeddings: CLIP via fastembed
| Fact | Tag |
|---|---|
| fastembed 0.8.1 (22 Sep 2026), Python ≥ 3.10 | [VERIFIED: https://pypi.org/project/fastembed/] |
| `Qdrant/clip-ViT-B-32-vision` (512-d, 0.34 GB) pairs with `Qdrant/clip-ViT-B-32-text` (512-d, 0.25 GB) | [VERIFIED: fastembed 0.8.1 source, `list_supported_models()` run locally] |
| Alternatives: google/siglip2-base-patch16-224 (768-d, text model 1.13 GB), jinaai/jina-clip-v1 (768-d), nomic-embed-vision-v1.5 (768-d) | [VERIFIED: same] |
| Model cache: `cache_dir` or `FASTEMBED_CACHE_PATH`. The default is the system temp folder, which is not persistent. | [VERIFIED: fastembed 0.8.1 source `common/utils.py`] |
| `HF_HUB_OFFLINE=1` forces local files only | [VERIFIED: fastembed 0.8.1 source `common/model_management.py`] |

**Our benchmark:** Intel i5-13450HX laptop, 16 cores, 7.6 GB RAM, WSL2, 14 Wikimedia sample images. [VERIFIED: `backend/bench-results/Monis-20260923-234840.json` and an offline re-run]

| Metric | Result |
|---|---|
| Model load (cached) | 2.4 s |
| First download | ~17 min for ~580 MB (network-bound) |
| Per image (batched / single warm) | 32 ms / 45 ms |
| Per text query | 10–16 ms |
| Vectors | 512-d, **already L2-normalised** (norm = 1.0) |
| Zero-shot tagging (14 images, 11 labels + 3 negative labels) | top-1 **78.6%**, top-3 **85.7%** |
| Correct-label cosine vs best wrong-label cosine | 0.24–0.35 vs 0.20–0.31. **The ranges overlap, so no fixed cutoff separates them.** |
| Same-scene image pair vs different scenes | 0.89 vs 0.32–0.73 |

- **[ASSUMPTION]** Show tags as **"top-3 suggested"**, not threshold-based. Use about **0.80** image similarity as the provisional "same site" threshold for before/after pairs. It is based on a single same-scene pair, so it must be re-checked with our own photos.
- **[UNVERIFIED]** Speed on Dev B's laptop. Check: run `uv run python scripts/clip_benchmark.py` and commit the result.

### 2.2 LLMs (report text, change descriptions)
| Fact | Tag |
|---|---|
| Gemini free tier lists 3.8 / 3.7 / 3.6 / 3.5 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite and 2.5 models as "Free of charge" | [VERIFIED: https://ai.google.dev/gemini-api/docs/pricing] |
| 2.5 models are limited to users who already used them. Google recommends 3.5 Flash-Lite or 3.8 Flash for new projects. | [VERIFIED: https://ai.google.dev/gemini-api/docs/models] |
| Google **does not publish** free-tier RPM/RPD limits. View them in AI Studio. | [VERIFIED: https://ai.google.dev/gemini-api/docs/rate-limits] |
| Image input on the free tier | [UNVERIFIED]. Check: send one image request with a free key. |
| Free tier: "Content used to improve our products", human reviewers may read it, and "Do not submit sensitive, confidential, or personal information" | [VERIFIED: https://ai.google.dev/gemini-api/terms] |
| Groq free (gpt-oss-120b / 20b, qwen3.8-27b): 30 RPM, 1K RPD, 8K TPM, 200K TPD | [VERIFIED: https://console.groq.com/docs/rate-limits] |
| Groq's only vision model is `qwen/qwen3.8-27b`: max 3 images per request, each image counts as 2,048 tokens | [VERIFIED: https://console.groq.com/docs/vision] |
| Cerebras free: gpt-oss-120b and qwen-3.8-27b. 5 RPM, 30K TPM, 1M TPD. The qwen model accepts 2 images per request. | [VERIFIED: https://inference-docs.cerebras.ai/support/rate-limits] |
| OpenRouter `:free`: 20 RPM, 50 RPD (1,000 RPD after buying $10 of credit) | [VERIFIED: https://openrouter.ai/docs/api-reference/limits] |
| LiteLLM prefixes `gemini/`, `groq/`, `cerebras/`. Router `fallbacks` with `num_retries`. `response_format` json_schema / Pydantic. | [VERIFIED: https://docs.litellm.ai/docs/providers/gemini], [VERIFIED: https://docs.litellm.ai/docs/routing], [VERIFIED: https://docs.litellm.ai/docs/completion/json_mode] |

- **[ASSUMPTION]** Because of the Gemini free-tier data terms, **no identifiable photos go to Gemini.** Send face-blurred derivatives (`e_blur_faces`) or text-only metrics.
- **[ASSUMPTION]** The LLM writes **prose only**. All numbers come from our own computed metrics through templates. This prevents invented statistics.

---

## 3. Application stack

| Fact | Tag |
|---|---|
| Next.js 16 is the current major (21 Oct 2025). The latest patch is 16.3.6 (22 Sep 2026). App Router is the default. Needs Node ≥ 20.9. | [VERIFIED: https://nextjs.org/blog/next-16], [VERIFIED: https://nextjs.org/blog] |
| `next/dynamic` with `ssr:false` is **not allowed in Server Components**. It must be used inside a Client Component. | [VERIFIED: https://nextjs.org/docs/app/guides/lazy-loading] |
| FastAPI 0.141.1. A `def` endpoint runs in a threadpool. An `async def` endpoint runs on the event loop, so blocking CPU work there freezes the server. | [VERIFIED: https://fastapi.tiangolo.com/release-notes/], [VERIFIED: https://fastapi.tiangolo.com/async/] |
| CORS: `allow_credentials=True` can't be combined with `["*"]`. `allow_methods` defaults to GET only. | [VERIFIED: https://fastapi.tiangolo.com/tutorial/cors/] |
| shadcn/ui defaults to Tailwind v4 + React 19 | [VERIFIED: https://ui.shadcn.com/docs/tailwind-v4] |
| shadcn/ui explicitly supports Next 16 | [UNVERIFIED]. Check: run `pnpm dlx shadcn@latest init` in `web/`. |
| react-leaflet 5.0.0 requires React ^19 and leaflet ^1.9 (1.9.4) | [VERIFIED: https://react-leaflet.js.org/docs/start-installation/] |
| OSM tiles: visible attribution, a valid User-Agent and Referer, no bulk or offline downloads, no SLA | [VERIFIED: https://operations.osmfoundation.org/policies/tiles/] |
| react-compare-slider 4.0.0, peer dependency react ≥ 16.8, MIT | [VERIFIED: https://github.com/nerdyman/react-compare-slider] |
| react-compare-slider explicitly tested on React 19 | [UNVERIFIED]. Check: the v4 release notes, or render it once. |
| `print-color-adjust` is Baseline (no prefix) | [VERIFIED: https://developer.mozilla.org/en-US/docs/Web/CSS/print-color-adjust] |
| @react-pdf/renderer 4.9.0 supports React 19 from 4.1.0 | [VERIFIED: https://react-pdf.org/compatibility] |

---

## 4. Database

| Fact | Tag |
|---|---|
| Neon Free: 0.5 GB storage per project, 100 CU-hours per project per month, 100 projects, 5 GB egress | [VERIFIED: https://neon.com/pricing] |
| Neon Free scales to zero after 5 minutes idle, and this can't be disabled | [VERIFIED: https://neon.com/docs/introduction/plans] |
| Neon pgvector 0.8.0 (Postgres 14–17) / 0.8.6 (Postgres 18). Enable with `CREATE EXTENSION IF NOT EXISTS vector;` | [VERIFIED: https://neon.com/docs/extensions/pg-extensions], [VERIFIED: https://neon.com/docs/extensions/pgvector] |
| Neon pooler = PgBouncer in transaction mode. No SQL `PREPARE`, `SET`, `LISTEN` or temp tables. Use the **direct** connection for migrations. | [VERIFIED: https://neon.com/docs/connect/connection-pooling] |
| Supabase Free: 500 MB database, 1 GB files, 50k auth MAU, 2 projects, **paused after 1 week inactive** | [VERIFIED: https://supabase.com/pricing] |
| pgvector: `<=>` = cosine distance. HNSW is faster to query than IVFFlat but slower to build. Indexes support at most 2,000 dims. | [VERIFIED: https://github.com/pgvector/pgvector] |
| pgvector-python: `from pgvector.sqlalchemy import VECTOR`, `.cosine_distance()` | [VERIFIED: https://github.com/pgvector/pgvector-python] |

---

## 5. Hosting, jobs, CI

### 5.1 Backend hosting (needs ≥ 1–2 GB RAM for CLIP)
| Option | Facts | Tag |
|---|---|---|
| Hugging Face Spaces (Docker) | **Docker and Gradio Spaces now require PRO ($9/month).** CPU Basic is 2 vCPU / 16 GB. It sleeps after 48 h without use. | [VERIFIED: https://huggingface.co/docs/hub/spaces-overview], [VERIFIED: https://huggingface.co/pricing] |
| Render Free | 512 MB RAM, sleeps after 15 min, ~1 min cold start, 750 hours/month | [VERIFIED: https://render.com/pricing], [VERIFIED: https://render.com/docs/free] |
| Koyeb Free | 0.1 vCPU, 512 MB, scales to zero after 1 h | [VERIFIED: https://www.koyeb.com/docs/reference/instances] |
| Railway | 30-day trial with $5, then $1/month credit and 0.5 GB RAM | [VERIFIED: https://railway.com/pricing] |
| Fly.io | Trial only (2 VM-hours or 7 days) | [VERIFIED: https://fly.io/docs/about/free-trial/] |
| Google Cloud Run | Has a free tier, but needs a billing account, and the trial needs a card | [VERIFIED: https://cloud.google.com/run/pricing], [VERIFIED: https://cloud.google.com/free/docs/free-cloud-features] |
| Oracle Always Free | A1 ARM: 1,500 OCPU-hours and 9,000 GB-hours per month (~2 OCPU, ~12 GB continuous). A card is required. Idle instances can be reclaimed. | [VERIFIED: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm], [VERIFIED: https://www.oracle.com/cloud/free/] |
| Azure for Students | $100 credit, no card, full-time students only | [VERIFIED: https://azure.microsoft.com/en-us/free/students] |
| Local laptop + Cloudflare quick tunnel | Free, dev/testing only, 200 in-flight requests at most | [VERIFIED: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/] |
| ngrok Free | $5 one-time usage, 1 GB transfer, 20k requests, interstitial page | [VERIFIED: https://ngrok.com/pricing] |

- **[ASSUMPTION]** CLIP needs over 512 MB of RAM, so Render, Koyeb and Railway free tiers are ruled out. Inferred from 0.59 GB of model files plus onnxruntime. Not measured.
- **[UNVERIFIED]** Whether onnxruntime has ARM64 Linux wheels (relevant for Oracle). Check: `pip download onnxruntime --platform manylinux2014_aarch64 --only-binary=:all:`.

### 5.2 Frontend hosting
| Fact | Tag |
|---|---|
| Vercel Hobby: **non-commercial personal use only**, 300 s functions, 100 GB transfer, 1M invocations | [VERIFIED: https://vercel.com/docs/plans/hobby] |
| Netlify Free: 300 credits/month (a production deploy costs 15) | [VERIFIED: https://www.netlify.com/pricing/] |
| Cloudflare Workers Free: 10 ms CPU per request, 128 MB memory | [VERIFIED: https://developers.cloudflare.com/workers/platform/limits/] |

- **[ASSUMPTION]** A hackathon submission counts as non-commercial, so Vercel Hobby is acceptable.

### 5.3 Background jobs
| Fact | Tag |
|---|---|
| FastAPI BackgroundTasks run in-process. The docs recommend Celery-class tools for heavy work. | [VERIFIED: https://fastapi.tiangolo.com/tutorial/background-tasks/] |
| Procrastinate 3.9.0: a Postgres-based task queue for Python 3.10+ and Postgres 13+ | [VERIFIED: https://procrastinate.readthedocs.io/en/stable/] |
| Postgres `FOR UPDATE SKIP LOCKED` is documented for queue-like tables | [VERIFIED: https://www.postgresql.org/docs/current/sql-select.html] |
| Upstash Redis Free: 500K commands/month. BullMQ-style polling burns commands even when idle. | [VERIFIED: https://upstash.com/pricing/redis], [VERIFIED: https://upstash.com/docs/redis/integrations/bullmq] |
| Inngest Free: 50k executions, Python SDK 0.5.19 | [VERIFIED: https://www.inngest.com/pricing] |

### 5.4 CI
| Fact | Tag |
|---|---|
| GitHub Free: 2,000 Actions minutes/month for private repos | [VERIFIED: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions] |

### 5.5 Auth (only if needed)
| Fact | Tag |
|---|---|
| Auth.js v5 is still beta (5.0.0-beta.32). The project is now part of Better Auth. | [VERIFIED: https://authjs.dev/getting-started/migrating-to-v5] |
| Better Auth: MIT, supports Next 14–16 | [VERIFIED: https://github.com/better-auth/better-auth] |
| Clerk Hobby: 50,000 monthly retained users per app, free | [VERIFIED: https://clerk.com/pricing] |
| Neon Auth (built on Better Auth): 60k MAU on Free | [VERIFIED: https://neon.com/docs/introduction/plans] |

---

## 6. Final stack decision table

### 6.1 🔒 LOCKED (already chosen by the team)
| Layer | Choice | Reason | Rejected alternatives | Free-tier limits that affect us |
|---|---|---|---|---|
| Frontend framework | **Next.js 16 (App Router) + TypeScript** | Official `next-cloudinary` components; stable; large community | TanStack Start (still RC), Vite SPA (no Cloudinary wrapper) | Vercel Hobby is non-commercial |
| Cloudinary UI | **next-cloudinary** (CldUploadWidget, CldImage, CldVideoPlayer) | Official; handles widget loading | Hand-wired widget script | — |
| UI kit | **Tailwind v4 + shadcn/ui** | Default for new projects, React 19 ready | Tailwind only, Mantine | — |
| JS package manager / lint | **pnpm / ESLint** | Team choice | npm, bun / Biome | — |
| Backend | **Python 3.12 + FastAPI, managed by uv** | CLIP, Pillow and EXIF tooling are Python | Node-only backend | — |
| DB access | **SQLAlchemy 2.0 + psycopg 3 + pgvector-python** | Official pgvector support | SQLModel, raw SQL | — |
| Embeddings | **fastembed CLIP ViT-B/32 (vision + text, 512-d)** | Benchmarked: 32 ms per image, normalised, 79% top-1 | SigLIP2 (text model 1.13 GB), jina-clip | ~580 MB of models on disk |
| Repo | **Monorepo: backend/ + web/ + docs/** | Shared code with PS1 later | Separate repos | — |

### 6.2 🟡 PROPOSED (needs team approval; options listed, recommendation first)
| Layer | Recommended | Option 2 | Option 3 | Why the recommendation |
|---|---|---|---|---|
| Database | **Neon Free + pgvector** | Supabase Free | Local Postgres | Neon doesn't pause for a week (it scales to zero and wakes in ~seconds) [VERIFIED above]. Supabase pauses after 1 week inactive. |
| Semantic search | **CLIP vectors in pgvector, exact scan (no index)** | HNSW index | Qdrant Cloud | One database. Under ~10k rows an exact scan is fine [ASSUMPTION]. |
| Tagging | **CLIP zero-shot top-3 + Cloudinary `coco_v2` detection in the preset** | + Google Auto Tagging add-on | + AI Vision tagging | CLIP never runs out. Cloudinary adds "Cloudinary-native" AI for judging. The add-on quotas are UNVERIFIED. |
| LLM (text) | **LiteLLM: Gemini 3.5 Flash-Lite → Groq gpt-oss-20b → Cerebras gpt-oss-120b** | Groq only | Gemini only | Three independent free quotas. LiteLLM handles fallbacks [VERIFIED above]. |
| LLM (vision, optional) | **Groq `qwen3.8-27b` on face-blurred images** | Gemini Flash (face-blurred) | No vision LLM (metrics-only text) | Groq's vision model is documented [VERIFIED]. Gemini free-tier image input is UNVERIFIED and has data-use terms. |
| Background jobs | **Postgres `jobs` table + `SKIP LOCKED` worker loop** | Procrastinate | FastAPI BackgroundTasks | No Redis. Survives restarts. Simple to explain. |
| Backend hosting | **Laptop + Cloudflare quick tunnel for the demo; Azure for Students if eligible** | Oracle Always Free (needs a card) | HF Spaces PRO ($9/month ⚠ cost) | Free options with enough RAM are scarce [VERIFIED above]. |
| Frontend hosting | **Vercel Hobby** | Netlify Free | Run locally only | Native Next.js hosting, and non-commercial use fits a hackathon [ASSUMPTION]. |
| Map | **Leaflet + react-leaflet 5 + OSM tiles** | MapLibre + free tiles | Static map image | Free, React 19 compatible [VERIFIED]. |
| Before/after slider | **react-compare-slider 4** | img-comparison-slider | Hand-built | MIT, small, React ≥ 16.8 peer [VERIFIED]. |
| Report export | **Browser print-to-PDF with print CSS** | @react-pdf/renderer | Server-side PDF | Zero extra code paths, and `print-color-adjust` is Baseline [VERIFIED]. |
| Auth | **None: a single demo organisation** | Better Auth (email + password) | Clerk Hobby | Auth adds build time without covering any Goal bullet [ASSUMPTION]. It can be added for the offline round. |
| CI | **GitHub Actions: lint + pytest on push** | None | — | 2,000 free minutes [VERIFIED]. It catches broken pushes between two developers. |

### 6.3 ⚠ Items that cost money (all avoided)
| Item | Cost | Free alternative used |
|---|---|---|
| HF Spaces Docker hosting | $9/month (PRO) | Laptop + tunnel / Azure for Students / Oracle |
| Cloudinary paid plans / larger add-on tiers | Paid | Free plan, a fixed transformation set, CLIP fallback |
| Cloudinary DAM visual search | Enterprise | CLIP + pgvector |
| OpenRouter 1,000 RPD tier | $10 one-time | Gemini, Groq and Cerebras free tiers |
| Oracle Always Free | $0, but a card is required | Laptop + tunnel |

---

## 7. Risks surfaced by research (detailed in 06-risks)
1. **Deadline conflict (30 Sep vs 3 Oct)** [UNVERIFIED which applies].
2. **No free host with enough RAM for CLIP** that needs no card and isn't student-only [VERIFIED facts, ASSUMPTION on RAM need].
3. **Add-on free quotas unknown** [UNVERIFIED].
4. **CLIP zero-shot is only ~79% top-1**, with overlapping score ranges [VERIFIED by benchmark].
5. **Gemini free-tier data terms** conflict with sensitive NGO photos [VERIFIED].
6. **Account disabled if credits are exceeded** [VERIFIED].

## 8. Checks to run first (all [UNVERIFIED] above)
1. Which deadline is binding (ask the organisers).
2. Cloudinary Console → Add-ons: free quotas for Google, AWS and Imagga tagging, AI Content Analysis, AI Vision, video tagging and transcription.
3. Does `g_auto` work on our Free account? (one test URL)
4. Does generative AI (`e_gen_remove`) work on Free? (one test URL; costs 50 transformations)
5. Free-plan synchronous video transformation size limit (one 60 MB test clip).
6. Gemini free-tier image input (one API call with a test image).
7. shadcn/ui init on Next 16, and react-compare-slider on React 19 (quick install test).
8. Actual RAM used by the CLIP backend (measure with `ps` once the backend loads both models).
9. onnxruntime ARM64 wheel availability (only if Oracle is chosen).
10. Dev B's laptop benchmark.
11. Eligibility for Azure for Students (is either developer a full-time student?).

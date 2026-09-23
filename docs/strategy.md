# Code Cubicle 6.0 — Strategy & Build Plan (v2)

_Updated 23 Sep 2026 after the official notice that updated the prizes and the deadline. Sources are at the bottom._

## What changed in v2
- **Rules:** you may choose **at most 1 General PS plus the Cloudinary PS**. PS1 and PS3 are both General, so **PS1 + PS3 is not allowed**. v1 of this plan is void.
- **Prizes:**
  - Cloudinary PS (PS2): **₹1.4L** in Amazon vouchers.
  - Code Cubicle pool (General PS): **₹30K**.
  - PS2 is now worth about 4.7× more.
- **Deadline:** submissions close on **30 Sep**. From today that is **8 days including today**.
- **Mentors:** the organisers are assigning mentors, and asked teams to submit early.

**Assumptions** (edit if wrong)
- Both developers know TypeScript/React and Python, and can give 6–8 hours a day.
- **PS1 stays the General pick**, as you said.
- The offline round is still on 11 Oct. The notice doesn't mention it, so ask in the WhatsApp group.
- The updated PDF may have reworded the problem statements. Check it against `problem-statements.md`, because this plan uses the old text.

---

## 1. Verdict

**Do PS1 (General) + PS2 (Cloudinary), split 50/50. Each developer owns one PS end-to-end, on a shared core.**

- **Rules:** PS3 can no longer be paired with PS1, so the choice is PS1 alone or PS1 + PS2.
- **Prize:** PS2 alone carries ₹1.4L.
- **Reuse:** PS2 reuses PS1's backend, LLM layer, job pipeline, dashboard shell and Postgres. PS2 adds pgvector for semantic search.
- **Cost:** PS2's cost risk is real but manageable:
  - We run **our own semantic search** (local CLIP embeddings + pgvector), because Cloudinary's visual search is Enterprise-only.
  - We keep the demo dataset small (about 150 images and a few short SD videos).
  - We use generative-AI transformations only a handful of times.
- **Honest caveat:** two PSs in 8 days is tight. PS1 stays deliberately boring so PS2 can be polished, because PS2 is where the money is.
- **Checkpoint:** if either PS's MUST list isn't working by **Sun 27 Sep night**, both developers swarm on PS2. It carries the bigger prize, and PS1 is then submitted at whatever state it has reached.

## 2. Scoring table

The scale is 1–5, and higher is always better for us.

| PS | Build effort | Cost | Tech risk | Demo impact | Reuse with PS1 | Prize | Eligible alongside PS1? |
|---|---|---|---|---|---|---|---|
| **PS1** Data Intelligence | 3 | 4 | 4 | 4 | — | ₹30K pool (General) | — |
| **PS2** Cloudinary Media | 3 | 3 (25 credits/mo; AI add-on quotas unverified) | 3 | 5 | 3 (backend, LLM, jobs, DB, UI shell) | **₹1.4L pool** | ✅ |
| **PS3** Qdrant Edge | 2 | 5 | 2 (beta, DIY sync) | 4 | 4 | ₹30K pool (General) | ❌ both are General |

---

## 3A. PS1: "Scout" — AI Data Intelligence Platform (owner: Dev A)

### Pitch
Scout turns a plain-English request into a clean, source-backed dataset.

1. An LLM turns the request into an editable **collection plan**: the output schema, search queries, allowed domains and validation rules.
2. A background job searches permitted sources, fetches the pages (respecting robots.txt), and extracts records to the schema.
3. The job validates and deduplicates the records. Each row keeps a link to the page and the snippet it came from.
4. The dashboard shows live progress, filters, search, source inspection, task history with re-run, and CSV/JSON export.

### Architecture

```
 React (Vite + TS + Tailwind + shadcn/ui + TanStack Table)   ← Vercel Hobby
        │ REST + SSE
        ▼
 FastAPI (Python 3.11)                                     ← local for demo; Render free as hosted link
   ├─ Planner: prompt → Plan JSON {schema, queries, domains, rules}
   ├─ core/jobs: `jobs` table + worker (SELECT … FOR UPDATE SKIP LOCKED)
   └─ pipeline: search (Tavily → Serper → ddgs)
               → fetch (Crawl4AI → Jina Reader)
               → robots.txt + domain allow/deny
               → LLM extract → pydantic validate → rapidfuzz dedupe
               → store records + sources(url, snippet, fetched_at)
 Postgres: Neon free (0.5 GB)          LLM: LiteLLM router Groq → Cerebras → Gemini Flash → Ollama
```

**Budget rules:**
- Cap each task at **25 pages**, and trim each page to the relevant ~6K characters.
- Cache LLM calls by content hash.
- Groq's free tier gives about 200K tokens a day **per model**, so plan with gpt-oss-120b and extract with gpt-oss-20b. That gives two separate token budgets.

### MVP features

| Feature | Goal bullet it satisfies | Tag |
|---|---|---|
| Prompt → editable plan card | Understand NL; design workflow | **MUST** |
| Background job: search → fetch → extract | Execute workflow; multiple sources | **MUST** |
| robots.txt + domain allow/deny, with blocked URLs in the log | Permitted sources | **MUST** |
| Validation, normalisation, fuzzy dedupe with a merged-sources count | Clean / structure / validate / dedupe | **MUST** |
| Source drawer per row (URL, snippet, time) | Traceable | **MUST** |
| Task list with live progress and log (SSE); cancel and re-run | Monitor and manage | **MUST** |
| Results table with search, filters and sort | Dashboard; search and filter | **MUST** |
| CSV/JSON export | Export | **MUST** |
| History: past tasks and plan versions, "re-run with edits" | History | **MUST** (simple) |
| Stats header (rows, duplicates removed, failed validation) | Dashboard | **SHOULD** |
| Scheduled re-runs + diff, per-field confidence | Manage / validate | **SHOULD** (offline round) |
| Auth, no-code workflow builder, proxies or captcha solving | — | **CUT** |

---

## 3B. PS2: "FieldProof" — Impact & Sustainability Media Platform on Cloudinary (owner: Dev B)

The name "ImpactLens" is already used by a public PS2 repo, so we avoid it.

### Pitch
FieldProof turns an NGO's messy dump of field photos and videos into **verifiable impact evidence**.

- **Ingest:** teams bulk-upload through the Cloudinary Upload Widget. On upload, each asset gets:
  - auto-tags from Cloudinary AI,
  - its capture time and GPS read from EXIF,
  - an assignment to a project site on a map, and a place on a timeline.
- **Search:** people search in plain language, e.g. *"flooded road near the school"* or *"saplings after monsoon"*, using CLIP embeddings.
- **Before/after:** FieldProof pairs before-and-after shots of the same site automatically. It aligns them with Cloudinary transformations and measures visible change, such as green-cover percentage.
- **Reports:** it generates an impact report and campaign-ready assets: social crops with `g_auto`, a before/after collage and a text-overlay card.
- **Traceability:** every output links back to its source asset and **the exact Cloudinary transformation URL** that produced it. Because Cloudinary encodes transformations in the URL, lineage comes for free.

### Architecture

```
 React shell (shared with Scout) — pages: Upload · Library · Map/Timeline · Search · Compare · Reports · Lineage
   └─ Cloudinary Upload Widget (unsigned preset) + Cloudinary Video Player
        │ webhook / notification_url on upload
        ▼
 FastAPI (same app skeleton, core/ shared)
   └─ ingest job per asset (core/jobs):
        1. fetch Cloudinary resource: tags (auto_tagging / detection:coco), image_metadata (EXIF GPS + date),
           colors, dimensions; for video: keyframes via so_ (start-offset) transformations
        2. CLIP embedding (fastembed clip-ViT-B-32, local CPU) → Postgres + pgvector (Neon free)
        3. project assignment: nearest project site by GPS (haversine) → else LLM on tags+caption → user confirms
        4. write back to Cloudinary: structured metadata (project, site, phase=before/after), tags
   ├─ Compare: pair assets (same project/site, time gap ≥ N days)
   │          → aligned renders: c_fill,g_auto,w_800,h_600 on both; side-by-side via l_ overlay
   │          → metrics (Pillow): green-cover %, brightness/water-pixel %, VLM change summary
   ├─ Reports: LLM (Groq/Gemini) writes summary from structured evidence only (no invented numbers)
   │          → campaign assets: g_auto social crops (1:1, 9:16), l_text overlay card, collage
   └─ Lineage: every derived item stores {source public_id, asset_id, version, transformation URL, model, timestamp}
 Map: Leaflet + OpenStreetMap tiles (free)
```

**Free tiers and budget**
- **Cloudinary Free** gives 25 credits a month. One credit is 1,000 transformations, 1 GB of storage or 1 GB of bandwidth.
- **Image budget:** 150 images and about 1,500 transformations is under 3 credits.
- **Video budget:** video is expensive. An HD transform costs 4 transformations per second, so keep 3–5 SD clips of 20–30 seconds each.
- **Generative AI:** use only a few times, for demo polish. It costs 50–230 transformations per use.
- **Add-on quotas are unverified.** The free tiers for Google and AWS auto-tagging, AI Vision and transcription show up only in the Console. **Check them on Day 1.**
- **If the quotas are too small:** tag images locally with **CLIP zero-shot** against a sustainability label list (sapling, solar panel, flood, road work, water pump, classroom, waste pile…). That costs ₹0 and has no quota.
- **Vision LLM** (for change summaries and captions): Gemini Flash free tier, whose quota is unverified. Fallback: template text built from the metrics.

### Demo dataset (start today; this is a real risk)
- **Public-domain satellite before/after pairs:** NASA Earth Observatory and USGS Landsat have floods, deforestation and lakes.
- **Wikimedia Commons CC-BY photos**, with attribution kept in metadata. That doubles as extra traceability.
- **Your own phone photos, with GPS on.** Stage one small real project, such as cleaning up a local park corner or planting saplings, and shoot the same framing before and after. That gives a genuine before/after pair with real EXIF data, which judges will like.

### MVP features

| Feature | Goal bullet it satisfies | Tag |
|---|---|---|
| Bulk upload (widget) → auto-tags + EXIF + CLIP embed pipeline, with progress | Analyse and organise large collections | **MUST** |
| Library grouped by project/site; map view; timeline view | Identify projects, locations; organise | **MUST** |
| Tags + detected objects as filters (activity, visual signals) | Identify activities / visual signals | **MUST** |
| Natural-language semantic search + tag/metadata filters | Searchable via AI metadata and semantic discovery | **MUST** |
| Before/after pairing + slider + green-cover % change | Compare before/after | **MUST** |
| Impact report page (summary + metrics + evidence grid) exported as HTML/PDF | Visual reports, summaries | **MUST** |
| Campaign kit: `g_auto` social crops + text-overlay card + collage | Campaign-ready content | **MUST** |
| Lineage panel: source → transformations → output, with clickable URLs | Traceability | **MUST** |
| Structured metadata written back to Cloudinary (project/site/phase) | Organise; Cloudinary-native | **SHOULD** (cheap; do it if time allows before 30 Sep) |
| Video: keyframe tagging + auto-transcription / chapters | Video evidence | **SHOULD** |
| Evidence integrity: perceptual-hash duplicate detection, missing-EXIF flag | Verify | **SHOULD** |
| Cloudinary MCP server in the report agent | Cloudinary-native bonus | **SHOULD** (offline round) |
| Generative "restore/cleanup" effects, multi-tenant orgs, mobile app | — | **CUT** |

---

## 4. Shared code (build once)

```
cc-hack/
├─ core/            # llm.py (LiteLLM router+cache) · jobs.py (table queue+worker) · events.py (SSE log)
│                   # db.py (SQLAlchemy, Neon Postgres + pgvector) · export.py (CSV/JSON/HTML report)
├─ scout/           # PS1 routes + pipeline            (Dev A)
├─ fieldproof/      # PS2 routes + ingest/compare/report (Dev B)
└─ web/             # one React app, two sections: AppShell, DataTable, JobProgress, LogStream,
                    # DetailDrawer (PS1 source / PS2 lineage), StatCard, StatusBadge
```

The same backend deployment serves both products, and one Neon database holds both schemas.

## 5. Day-by-day plan (deadline Wed 30 Sep)

| Date | Dev A (Scout + core) | Dev B (FieldProof + web shell) | Exit criterion |
|---|---|---|---|
| **Wed 23** | Monorepo; `core/` llm, jobs, events, db; accounts for Groq, Cerebras, Tavily, Serper, Neon (enable pgvector) and Jina | Cloudinary account + **quota check** for Google/AWS tagging, AI Vision and transcription; unsigned upload preset; React shell. **Start the dataset**: download NASA/Wikimedia pairs, shoot the "before" photos | Both skeletons run; Cloudinary AI plan decided (native tags or CLIP zero-shot) |
| **Thu 24** | Planner → Plan JSON; search + fetch + robots | Ingest job: upload webhook → tags + EXIF + CLIP → pgvector; library grid | 20 assets ingested and tagged |
| **Fri 25** | Extract → validate → dedupe → sources | Projects/sites, map + timeline, semantic search | NL search returns sensible hits |
| **Sat 26** | Tasks page + SSE, results table, source drawer | Before/after pairing, slider, metrics. Shoot the **"after"** photos | A real before/after pair with numbers |
| **Sun 27** | Export, history, re-run; 3 demo prompts pass | Report page, campaign kit, lineage panel | **Checkpoint:** both MUST lists complete, or both devs swarm PS2 |
| **Mon 28** | Hardening: retries, backoff, cache; deploy both (Vercel + Render + Neon) | Hardening; structured metadata write-back; seed ~150 assets | Deployed links work from a cold start |
| **Tue 29** | **Feature freeze.** README, architecture diagram, record Scout video | README, record FieldProof video; slides for both | Submission packages ready |
| **Wed 30** | **Submit by noon**, not at midnight. Confirm resubmission and edit rules with the mentor | same | Submitted ✅ |
| 1 – 10 Oct | *If shortlisted:* SHOULD items (video AI, integrity checks, MCP, scheduled re-runs); offline-proofing (cached demo replay); rehearsals ×3 | same | — |
| **11 Oct** | Offline round (confirm the date) | | |

## 6. Demo scripts (3 min each, since each PS is submitted separately)

**Scout (PS1)**
- **0:00:** Hook: "Describe the data you need; get a verified dataset."
- **0:10:** Type a request (AI startups in Bengaluru hiring ML engineers, with company, role, careers URL and stage). The plan card shows the schema, queries and domains. Edit one field and click Run. `[understand NL] [design workflow]`
- **0:40:** Show the live log and progress. Point out sources across careers pages, news and job boards, and one URL skipped by robots.txt. `[execute] [multiple permitted sources] [monitor]`
- **1:15:** Stats: 31 raw → 9 duplicates merged → 2 failed validation → 20 clean. `[clean/validate/dedupe]`
- **1:35:** Click a row. The source drawer shows the URL, highlighted snippet and fetch time. `[traceable]`
- **1:55:** Filter to Series A, search for "Koramangala", export CSV. `[dashboard] [search/filter/export]`
- **2:20:** On History, open last week's run, "re-run with edits", and cancel a running task. `[history] [manage]`
- **2:45:** Close on the ₹0 stack and the architecture slide.

**FieldProof (PS2)**
- **0:00:** Hook: "NGOs have thousands of photos and no proof. FieldProof turns them into evidence."
- **0:10:** Drop 40 photos and 2 videos into the Upload Widget. Assets stream in with auto-tags, dates and GPS. `[analyse/organise]`
- **0:35:** The map shows project sites with clusters, and there's a timeline strip. Filter by the tags "sapling" and "volunteers". `[projects, activities, locations, visual signals]`
- **0:55:** Search "waterlogged road near school" and get the right photos, including one with no matching tag. `[AI metadata + semantic discovery]`
- **1:20:** Open the Compare page for the park site: before/after slider, **green cover +18%**, and a VLM change summary. `[before/after]`
- **1:50:** Click "Generate impact report": summary, metrics and an evidence grid. Then the campaign kit: 1:1 and 9:16 crops with `g_auto`, plus a quote card. `[reports, campaign content]`
- **2:25:** Click any output to open the lineage panel. It shows the source asset, the exact transformation URL chain and the model used. "Every pixel is auditable." `[traceability]`
- **2:45:** Close on the Cloudinary features used and the credits consumed (under 5 of 25).

## 7. Top 5 risks and fallbacks

| # | Risk | Fallback |
|---|---|---|
| 1 | **Cloudinary AI add-on free quotas are tiny or unavailable** (unverified; one Cloudinary page says auto-tagging is paid-only) | Check on Day 1. The fallback is CLIP zero-shot tagging done locally (₹0). Keep Cloudinary for upload, EXIF, transformations, `g_auto`, overlays, video and structured metadata, which are the parts that impress Cloudinary judges anyway. Ask the mentor or WhatsApp group whether Cloudinary gives hackathon credits (see cld.media/hackathons) |
| 2 | **No good before/after data** | Start today: NASA/Landsat public-domain pairs, Wikimedia CC, and your own staged mini-project with GPS on. Don't leave the "after" shoot until the 29th |
| 3 | **Free LLM limits** (Groq ~200K tokens/day per model; Gemini free tier cut) | LiteLLM chain Groq → Cerebras → Gemini → Ollama. Page trimming, hash cache, page cap. PS2 reports are generated once and cached |
| 4 | **Scraping blocked / flaky Wi-Fi** | Crawl4AI with Jina fallback. Demo prompts on known-friendly sources. A "replay" mode that serves cached fetches, plus the backup video |
| 5 | **8 days for two PSs** | Each developer owns one PS on the shared core. Checkpoint on Sun 27 (swarm PS2 if behind). Freeze on the 29th. Submit by noon on the 30th |

## 8. Cost

| Item | Choice | Cost |
|---|---|---|
| LLM | Groq, Cerebras, Gemini free, Ollama | ₹0 |
| Search / scrape | Tavily 1k/mo, Serper 2.5k one-time, ddgs, Crawl4AI, Jina | ₹0 |
| Media | Cloudinary Free (25 credits/mo), with a budget of under 10 credits | ₹0 |
| Embeddings | fastembed CLIP + text models on local CPU | ₹0 |
| DB | Neon free Postgres + pgvector | ₹0 |
| Hosting / maps | Vercel Hobby, Render free, Leaflet + OSM | ₹0 |
| **Total** | | **₹0** |

**Avoid:**
- Cloudinary paid plans and the paid add-on tiers.
- Brave Search API, which now needs a card.
- Fly.io and Railway, which have no lasting free tier.
- Heavy generative-AI transformations.

Qdrant is no longer in the plan.

---

## Sources
- Cloudinary pricing / Free plan: https://cloudinary.com/pricing · credits: https://cloudinary.com/documentation/billing_and_plans · file limits: https://cloudinary.com/pricing/compare-plans · transformation counts (video, gen-AI): https://cloudinary.com/documentation/transformation_counts
- Cloudinary auto-tagging add-ons: https://cloudinary.com/documentation/google_auto_tagging_addon · https://cloudinary.com/documentation/aws_rekognition_auto_tagging_addon · AI Content Analysis: https://cloudinary.com/documentation/cloudinary_ai_content_analysis_automatic_tagging · AI Vision: https://cloudinary.com/documentation/cloudinary_ai_vision_addon
- Visual search is Enterprise-only: https://cloudinary.com/documentation/dam_visual_search · transcription: https://cloudinary.com/documentation/video_transcription
- Cloudinary MCP servers: https://github.com/cloudinary/mcp-servers · Next.js starter: https://cloudinary.com/documentation/nextjs_quick_start · Python SDK: https://pypi.org/project/cloudinary/
- Cloudinary "Pixels to Products" hackathon (also ₹1.4L; possibly the same pool, **unverified**): https://hackindia.org/2026/pixels-to-products-cloudinary-ai-hackathon-2026 · an existing PS2 repo: https://github.com/Mohitrath/impactlens-ai
- Groq limits: https://console.groq.com/docs/rate-limits · Cerebras: https://inference-docs.cerebras.ai/support/rate-limits · Gemini: https://ai.google.dev/gemini-api/docs/rate-limits
- Tavily: https://docs.tavily.com/documentation/api-credits · Brave dropping its free tier: https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/ · Crawl4AI: https://github.com/unclecode/crawl4ai · Jina: https://jina.ai/reader/
- Neon: https://neon.com/faqs/free-plan-limits-and-quotas · Render: https://render.com/docs/free · Vercel Hobby: https://vercel.com/docs/plans/hobby
- Code Cubicle (Geek Room): https://www.geekroom.in/ · 6.0 listing: https://www.startupnetworks.co.uk/links/link/30891-code-cubicle-6-0

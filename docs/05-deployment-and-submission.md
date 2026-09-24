# 05 — Deployment & Submission

_Tags: [VERIFIED: …] · [UNVERIFIED] · [ASSUMPTION]. **[R§x]** = 00-research. Deploy day: **Tue 29 Sep** (04-roadmap P5)._

---

## 1. Hosting plan (all ₹0)

| Piece | Host | Why | Limits that matter |
|---|---|---|---|
| Web (Next.js 16) | **Vercel Hobby** | Native Next.js hosting | Non-commercial use only [R§5.2] |
| API + worker (FastAPI, CLIP) | **Azure for Students VM** (Ubuntu) | $100 credit, no card; enough RAM for CLIP [R§5.1] | Credit-funded; VM size to choose (below) |
| Fallback API host | **Team laptop + Cloudflare quick tunnel** | Free, HTTPS URL, no account | Dev/testing only; 200 in-flight requests at most [R§5.1] |
| Database | **Neon Free** | pgvector, no weekly pause | 0.5 GB; scales to zero after 5 min [R§4] |
| Media | **Cloudinary Free** | Required by the PS | 25 credits over a rolling 30 days [R§1.1] |
| LLMs | Gemini / Groq / Cerebras free tiers | Fallback chain | [R§2.2] |

### 1.1 Azure VM sizing
- **RAM needed:** the API and the worker each load CLIP (~0.6 GB of model files), plus Python and onnxruntime overhead. [ASSUMPTION: aim for **≥ 4 GB RAM**]
- **Measure first:** on Day 1, run both processes locally and read their memory use (RSS) with `ps -o rss`.
- **Which VMs are free:** Azure for Students includes 750 h each of B1s, B2pts v2 and B2ats v2 for 12 months [R§5.1]. **Their RAM is [UNVERIFIED].** If they're under the measured need, choose a larger B-series VM paid from the $100 credit. Check prices on the Azure pricing calculator before creating the VM.
- **Region:** the closest to India that the student subscription allows [UNVERIFIED].

### 1.2 HTTPS for the API
The Vercel site is HTTPS, so the API must be HTTPS too, or the browser blocks the calls [ps2-edge-cases #117].
- 🟡 **Plan:**
  1. Give the VM a public IP with an Azure DNS name label, which yields a hostname under `cloudapp.azure.com`.
  2. Run **Caddy** as the reverse proxy on ports 80/443 → `127.0.0.1:8000`.
  3. Caddy obtains the TLS certificate automatically. [UNVERIFIED: the DNS-label hostname format, and Caddy auto-TLS working for it. Check on deploy day.]
- **Fallback:** `cloudflared tunnel --url http://localhost:8000` on the VM or a laptop gives an `https://*.trycloudflare.com` URL [R§5.1].
- **Firewall:** open only 22 (restrict it to our IPs), 80 and 443.

### 1.3 Processes on the VM
- 🟡 `systemd` services (restart on failure):
  - `fieldproof-api`: `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`
  - `fieldproof-worker`: `uv run python -m app.worker`
- **Env:** `backend/.env` on the VM, created by hand and never committed. Set `HF_HUB_OFFLINE=1` after the models are downloaded [R§2.1].
- **Models:** run `scripts/download_models.py` once on the VM.
- **Update procedure:**
  1. `git pull`
  2. `uv sync`
  3. `uv run python scripts/migrate.py`
  4. `sudo systemctl restart fieldproof-api fieldproof-worker`

### 1.4 Vercel
1. Import the repo, set the project root to `web/`, framework Next.js.
2. Env vars: the ones in 03 §5.2 (all `NEXT_PUBLIC_*`), with `NEXT_PUBLIC_API_BASE_URL` = the HTTPS API URL.
3. **Redeploy after changing any env var.** Public vars are inlined at build time [VERIFIED: https://nextjs.org/docs/app/guides/environment-variables].
4. Add the Vercel URL to the backend's `CORS_ORIGINS` [R§3].

### 1.5 CI (GitHub Actions, approved S5)
- `.github/workflows/ci.yml` runs on push and PR:
  - **Backend job:** `astral-sh/setup-uv` → `uv sync` → `uv run ruff check` → `uv run pytest` (unit tests only; tests marked integration are skipped in CI).
  - **Web job:** pnpm setup → `pnpm install --frozen-lockfile` → `pnpm lint` → `pnpm build`.
- **Budget:** 2,000 free minutes a month for private repos [R§5.4].
- No auto-deploy from CI: Vercel deploys itself from git, and the VM is updated by hand. 🟡 [ASSUMPTION: simpler and safer for 7 days]

---

## 2. Credit and quota budget for deployment and demo
| Resource | Budget | How we stay under it |
|---|---|---|
| Cloudinary credits | ≤ 10 of 25 | ~150 images + 3–5 SD clips (≤ 30 s); fixed named transforms; no generative AI [R§1.2] |
| Cloudinary add-on (detection) | Recorded Day 1 | Switch to the `fp_image_basic` preset when it runs low (LLD §4.1) |
| Admin API | < 500/h | 1 call per asset; usage cached 5 min [R§1.1] |
| LLM calls | Gemini RPD unknown; Groq 1K RPD | Every text cached in `llm_cache`; the demo reads cache only |
| Neon | 100 CU-h/month | Demo-day warm-up call; nothing polls the DB when idle except the worker (1 s sleep). [ASSUMPTION: a 1 s poll keeps Neon awake while the worker runs. Stop the worker when not demoing to save CU-hours.] |

---

## 3. Seed and demo data plan
| Set | Source | Count | Licence handling |
|---|---|---|---|
| **Own before/after** (hero) | Team photos of one real site, phone camera with location on, same spot and angle; "before" 24 Sep, "after" 27 Sep | 6–10 | Ours; faces avoided or blurred |
| Activity photos | Wikimedia Commons (the benchmark set + more per label) | ~100 | CC BY / BY-SA / CC0 / PD. Title, author, source and licence kept in `samples/public/CREDITS.md` and shown on a Credits page [ps2-edge-cases #120] |
| Satellite before/after | NASA Earth Observatory / Landsat, public domain | 2–3 pairs | Credit NASA; **no NASA logo**; no implied endorsement [ps2-edge-cases #120] |
| Short videos | Own phone clips, SD, ≤ 30 s | 3–5 | Ours |

- **Structure:** 1 project ("Green Neighbourhood Initiative" 🟡) with 3–4 sites (our real site + 2–3 named sites placed at the Wikimedia photos' locations or set by hand).
- **`seed_demo.py`:** creates the project and sites, uploads through the backend (signed upload with the same folder and preset settings), registers the assets, waits for analysis, builds 2–3 comparisons and 1 report, and pre-generates the campaign kit. After that, every URL and text exists, so **the demo creates nothing new**.
- 🟡 **`DEMO_MODE=true` during judging:** read-only, cached results only (LLD §9).

---

## 4. Demo script (≤ 3 min, covers every Goal bullet)

| Time | Screen | Say / do | Goal |
|---|---|---|---|
| 0:00 | Dashboard | "NGOs sit on thousands of photos. FieldProof turns them into proof." Show the project, asset counts and the credit meter. | — |
| 0:10 | Upload | Drop 5 photos + 1 video; the status goes pending → ready live. | **G1** |
| 0:35 | Asset detail | Suggested tags (CLIP) + Cloudinary detection tags, EXIF date, GPS → site auto-assigned; one no-GPS photo pinned by hand. | **G2** |
| 0:55 | Map + Timeline | Sites with counts; evidence over time; filter by tag "sapling". | **G1, G2** |
| 1:10 | Search | "waterlogged road near a school" → the right photo, **including one with no matching tag**; add a date filter. | **G5** |
| 1:35 | Compare | Our real site: the suggested pair → slider → **"Estimated green cover +15%"**, mask toggle, AI sentence; show the framing warning on a bad pair. | **G3** |
| 2:05 | Report | Generate (cached): headline, metrics, evidence grid, comparisons → Print → PDF. "Every number comes from the data; the AI only writes prose." | **G4** |
| 2:25 | Campaign kit | 1:1 and 9:16 smart crops, quote card, before/after collage, faces blurred. | **G4** |
| 2:40 | Lineage panel | Click the collage → source assets (public_id, version) → exact Cloudinary transformation URL → model and time; open the URL. | **G6** |
| 2:55 | Close | "Free stack, Cloudinary-native, traceable end to end." | — |

**Backup:** the recorded video (P5) plus the laptop + tunnel runbook (§1.2).

---

## 5. Pre-submission verification (Tue 29 Sep evening)
1. Fresh browser (incognito), on the public Vercel URL, on mobile data: run the full demo script.
2. `/health` on the public API: database ok, `clip_models_downloaded` true, Cloudinary configured.
3. Cloudinary usage < 50%. Every demo URL has already been generated once (cached).
4. `pnpm build` and `uv run pytest` are green in CI.
5. Stop the worker, restart the VM, confirm both services come back (systemd).
6. Credits page lists every non-original image.

## 6. Submission checklist (Wed 30 Sep, by 12:00)
- [ ] Repo is accessible to the judges (make it public, or add the judges, per the organisers' instructions [UNVERIFIED: ask which]).
- [ ] `README.md`: one-line pitch, feature list mapped to G1–G6, architecture diagram (from 01-hld), tech stack, a run-locally section (from 03 §6), live URL, demo video link, credits, team.
- [ ] Live URL works (web + API).
- [ ] Demo video (≤ 3 min) uploaded (unlisted YouTube or Drive) and linked.
- [ ] Slides / presentation, if required [UNVERIFIED: confirm the format with the organisers].
- [ ] The submission form is filled on the official platform (HackCulture / whatever the organisers specify) [UNVERIFIED: confirm the platform and fields].
- [ ] No secrets in the repo: search the history for `CLOUDINARY_URL=cloudinary://`, `API_KEY` and `api_secret`. Rotate any key that was ever committed.
- [ ] `DEMO_MODE=true` on production during judging.
- [ ] Screenshot of the submission confirmation saved.

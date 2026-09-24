# Getting Started: Who Does What

_Role split based on hardware: this machine (16 cores, plenty of RAM) handles backend/AI; his laptop (i5-7200U, 8 GB, only ~500 MB free) handles frontend. Matches Dev A / Dev B in [04-roadmap.md](04-roadmap.md)._

- **You = Dev A** — backend, AI/CLIP, database, Cloudinary server-side logic, deploy.
- **Him = Dev B** — frontend (Next.js), Cloudinary console setup, UI, upload flow.

Full task breakdown with dependencies and tests: [04-roadmap.md](04-roadmap.md) (Day 1 + Phases P0–P7). This doc is just "who starts on what, right now."

---

## You (Dev A) — do now
1. `cd backend && uv sync` (already done here).
2. Create Neon project → put the **direct** URL in `backend/.env` (see [03-project-structure.md](03-project-structure.md) §6.5).
3. `uv add cloudinary litellm` and `uv add --dev ruff`.
4. Write `migrations/0001_init.sql` from [02-lld.md](02-lld.md) §2, and `scripts/migrate.py`, then run it.
5. Confirm `/health` shows `database.status: ok`, `pgvector: true`.
6. Build `core/jobs.py` (enqueue/claim/complete/fail) + `worker.py`, test with a dummy job.
7. Then move into P1 (roadmap): `metadata.py`, `embeddings.py`, `cloudinary_gw.py`, `analyze_asset` pipeline.

You don't need him for any of this — it's all backend, independent of his machine.

## Him (Dev B) — do now
1. **Install WSL2 first** (native Windows had known onnxruntime issues in our research, and Node/pnpm also runs better there). PowerShell as admin → `wsl --install` → reboot.
2. Inside WSL/Ubuntu: clone the repo into `~/cc-hack` (not `/mnt/c` — slow).
3. Install pnpm: `npm i -g pnpm` (Node comes with recent Ubuntu, or install via nvm if missing).
4. `cd web && pnpm install`.
5. Cloudinary Console (his account or shared team account — confirm which):
   - Register the AI Content Analysis add-on, **write down its free quota**.
   - Create 3 unsigned presets: `fp_image`, `fp_image_basic`, `fp_video` (exact settings in [02-lld.md](02-lld.md) §4.1).
   - Test one `g_auto` URL and one `e_blur_faces` URL, record whether they work.
6. `pnpm dlx shadcn@latest init`, then `pnpm add next-cloudinary leaflet react-leaflet react-compare-slider`.
7. Build the AppShell + empty routes (sidebar, all pages listed in [03-project-structure.md](03-project-structure.md) §3), and a health-check widget calling your `/health` endpoint (he'll need your machine's local IP or a tunnel URL to reach it until the backend is deployed — coordinate this).
8. Then move into P1 (roadmap): Upload page wired to `CldUploadWidget`.

**He does not need to run the CLIP benchmark** to do any of this — that's optional validation, not a dependency (see earlier discussion). If his laptop struggles even with plain Next.js dev server, that's useful to know early.

---

## Coordination points
- **Today:** share how he'll reach your backend (local network IP, or run `cloudflared tunnel --url http://localhost:8000` on your machine and give him the HTTPS URL). Put it in his `web/.env.local` as `NEXT_PUBLIC_API_BASE_URL`.
- **Sun 27 Sep night:** checkpoint — before/after flow (J1–J4) must work end to end, or scope gets cut (see roadmap "Cut order if behind").
- **Git:** you both push to the shared private repo; pull before starting each session.

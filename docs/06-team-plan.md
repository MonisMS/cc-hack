# 06 — Team plan: who does what until submission

_Written 28 Sep 2026, evening. **Deadline: Wed 30 Sep, 12:00** (aim to submit by 11:00)._
_Task numbers (T16, T21, …) refer to `docs/04-roadmap.md`. If this doc and the roadmap disagree, this doc wins for **who** does it and the roadmap wins for **how**._

| Person | Role | Works with |
|---|---|---|
| **Monis** | Owner. Backend, demo data, deploy, merging PRs, submission | Claude |
| **Ujjwal** | Main frontend pages (library, asset, compare, report) | Claude |
| **Chaubey** | Credits page, demo photos, README draft | any AI tool |
| **Aditya** | Search page, testing, screenshots, demo video help | any AI tool |

---

## 1. Rules for everyone (read first)

1. **Nobody waits for anybody.** Every task below can be started right now. If something you'd like to reuse isn't merged yet, build a simple version inside your own file instead of waiting.
2. **Only touch the files listed as yours** (see §7). This is what stops merge conflicts. If you think a shared file (like `web/lib/types.ts`) needs a change, message Monis instead of editing it.
3. **One branch + one PR per task.** Branch name: `<name>/<task>`, e.g. `aditya/search-page`. Open the PR against `master` on `MonisMS/cc-hack`. Monis reviews and merges.
4. Before starting a task: `git checkout master && git pull`. Before opening the PR: `git pull origin master` again, then run **`cd web && pnpm lint && pnpm build`**. Both must pass. Paste a screenshot of your page in the PR description.
5. **Never commit secrets.** No `.env`, no API keys, no `cloudinary://…` strings. You don't need the backend `.env` at all (see rule 7).
6. **Don't add npm packages.** Everything you need is already installed (shadcn/ui components, `lucide-react`, `next-cloudinary`, `react-compare-slider`).
7. **You don't run the backend.** Monis shares one API URL in the group (a tunnel from his laptop now, the Azure URL later). Put it in `web/.env.local`:
   ```
   NEXT_PUBLIC_API_BASE_URL=<the URL Monis shares>
   NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME=dx4cdhvcp
   NEXT_PUBLIC_CLOUDINARY_IMAGE_PRESET=fp_image
   ```
   Then `cd web && pnpm install && pnpm dev` and open http://localhost:3000. The green dot at the bottom-left of the sidebar means the API is reachable.
8. **Feature freeze: Tue 29 Sep, 20:00.** After that, only bug fixes get merged.

### Frontend cheat sheet (give this to your AI tool too)
- **Next.js 16.** Make every page a client component: first line `"use client";`. Read route params with `const { id } = useParams<{ id: string }>();` from `next/navigation`.
- **Call the API only through `api()`** from `@/lib/api`: `const data = await api<{ items: Project[] }>("/api/projects");`. For something that finishes later (a comparison or report being generated), use `usePoll(path, isDone)` from the same file.
- **Types** for every API response are in `web/lib/types.ts`. Use them; don't redefine them.
- **Images:** use a plain `<img src={url} />` with the URL the API gives you (`thumb_url`, `compare_url`, `url`, …). **Never build a Cloudinary URL yourself** and never add query params to one. It costs credits.
- **UI components** are in `web/components/ui/` (Button, Card, Badge, Input, Label, Select, Table, Dialog, Sheet, Tabs, Skeleton, Textarea, Separator). These are **Base UI**, not Radix: to use a Button as a dialog trigger, write `<DialogTrigger render={<Button>Open</Button>} />`, **not** `asChild`.
- **Toasts:** `import { toast } from "sonner"; toast.error("…")`. Show `err.message` when `err instanceof ApiErr`.
- Every list needs an **empty state** ("No assets yet — upload some") and a loading state (`<Skeleton />`).
- Look at `web/app/projects/[id]/page.tsx` and `web/app/projects/[id]/upload/page.tsx` as working examples.

---

## 2. Already done (Monis, 27–28 Sep)

**Backend: complete and frozen** (T01–T15). 40 tests passing, verified live against the real Cloudinary account and Neon DB.
- Upload → analysis pipeline: EXIF date/GPS, CLIP tags, embeddings, automatic site assignment, worker with retries.
- API: projects, sites, assets (list/detail/edit/reprocess), jobs, semantic search, pair suggestions, before/after comparisons (green-cover %, masks, description), reports (metrics + summary), campaign kit (SQUARE/STORY/COLLAGE), lineage, Cloudinary credit guard.
- LLM gateway with a "no invented numbers" guard and a template fallback (works with no LLM keys).
- 69 demo assets seeded across 4 India sites.

**Frontend: started** (T17–T20).
- shadcn/ui setup, API client (`lib/api.ts`), types (`lib/types.ts`), app shell with sidebar + API health dot.
- Dashboard (project cards, "New project"), project overview (sites table, "Add site", reports list, "New report").
- Upload page: consent checkbox, "Use my location", Cloudinary upload widget, live status list. Tested with a real upload that reached `ready`.

---

## 3. Monis — the critical path

| # | Task | When | Notes |
|---|---|---|---|
| M1 | Push this plan. Add Ujjwal, Chaubey and Aditya as collaborators (or tell them to fork). Turn off the `@next/next/no-img-element` lint rule in `web/eslint.config.mjs` | **Now** | 10 min. Unblocks everyone's `<img>` tags |
| M2 | Run API + worker on the laptop and share a tunnel URL: `cloudflared tunnel --url http://localhost:8000` | **Now**, keep running while the team works | The tunnel URL changes on restart: re-share it if so |
| M3 | **T16** Demo data: Community Garden site from Chaubey's photos (C1), staged "before" date, 2–3 comparisons, 1 report, call the kit once. `DEMO_MODE` flag | 29 Sep morning | If the photos haven't arrived by 12:00, build the comparisons from seeded photos instead |
| M4 | **H4 + T27** Azure VM and backend deploy (Caddy HTTPS, systemd, swap). Stop the laptop worker first | 29 Sep afternoon | Then share the Azure URL (replaces M2) |
| M5 | **H5 + T28** Vercel project (root `web`), env vars, CORS on the VM | After M4 | |
| M6 | Review and merge PRs as they come in | All day 29 Sep | Merge Ujjwal's shared-components PR (U1) first |
| M7 | **H2** (optional, 5 min) Gemini/Groq keys in `backend/.env` so the text isn't template-only | Any time | Nice for the demo, not required |
| M8 | **T26** Full local demo run after the merges; fix blockers | 29 Sep, 18:00–20:00 | |
| M9 | 🔒 Feature freeze 20:00 → `DEMO_MODE=true` on the VM | 29 Sep, 20:00 | |
| M10 | **H6** Record the ≤ 3 min demo video, with Aditya (script: `docs/05` §4, skip map/timeline) | 29 Sep night | |
| M11 | **T29** Final README (start from Chaubey's draft C3) | 30 Sep morning | |
| M12 | **T30** Final checks + **H7** submission form + confirmation screenshot | 30 Sep, by 11:00 | |

---

## 4. Ujjwal — main frontend pages (with Claude)

Read `docs/04-roadmap.md` §3.1 (response shapes), §3.4 (Cloudinary rules) and §6 (gotchas) before starting. Point Claude at the task text in the roadmap; it has the full spec.

| # | Task | Files (yours) | Spec |
|---|---|---|---|
| **U1** | **Shared components. Do this first and open the PR tonight**, so the others can reuse them | `web/components/asset-card.tsx`, `asset-grid.tsx`, `tag-chips.tsx`, `status-badge.tsx`, `lineage-panel.tsx` | T21 first two bullets. `LineagePanel` = a `Sheet` that takes `entityType` + `entityId`, calls `GET /api/lineage?entity_type=&entity_id=` and shows each record as source → transformation (copy button) → output (link or image preview) → tool/model/time |
| **U2** | Library + asset detail | `web/app/projects/[id]/library/page.tsx`, `web/app/assets/[id]/page.tsx` | T21. Filters (site, tag, status), "Load more" with `next_cursor`, asset page with tags (add/remove manual), date + location with their sources, "Set location", "Move to site", "Reprocess" when failed, "Lineage" button |
| **U3** | Compare + comparison pages | `web/app/sites/[id]/compare/page.tsx`, `web/app/comparisons/[id]/page.tsx` | T23. Pair suggestions + manual pick, `ReactCompareSlider`, "Show green mask" toggle, "**Estimated** green cover X% → Y%", framing warning, description + "model: …" caption |
| **U4** | Report + print + campaign kit | `web/app/reports/[id]/page.tsx`, `web/app/reports/[id]/print/page.tsx`, the print CSS block at the end of `web/app/globals.css` | T24. Poll until ready; headline/paragraphs/highlights; metrics cards; before/after side by side; evidence grid; kit images with Download + Lineage; friendly message on `503 CREDIT_GUARD`. Print page: A4, hides the sidebar via `.no-print` |

- For U4 you'll need to add `className="no-print"` to the `<aside>` in `web/components/app-shell.tsx`. That one-line change is allowed; nobody else edits that file.
- To have data to look at: the seeded project **"Green Neighbourhood Initiative"** has 69 ready assets. For compare/report pages, create a comparison from a site's "Compare" page once U3 works, or ask Monis for the IDs from M3.
- **Target:** U1 tonight, U2 + U3 PRs by 29 Sep 15:00, U4 by 18:00.

---

## 5. Chaubey — credits page, photos, README draft

Simple tasks. Each one is independent.

### C1 · Before/after demo photos (no coding) — **29 Sep morning, in daylight**
This is the hero shot of the demo, so it matters a lot.
1. Phone camera settings → **Location / geotag ON**.
2. Pick one spot with plants (a garden, park strip or potted plants).
3. Take a **"before"** photo. Then change the scene visibly (add/remove plants, rearrange or water pots) and take the **"after"** photo **from exactly the same spot and angle**. Hold the phone at the same height.
4. Do **3–4 pairs**. Name them `before_1.jpg` / `after_1.jpg`, `before_2.jpg` / `after_2.jpg`, …
5. Send the **original files** to Monis via **Google Drive** (or as a WhatsApp "Document", not as a photo). ⚠️ Normal WhatsApp/Instagram photo sending **deletes the GPS data**. Don't commit them to git.
6. Tell Monis the rough location of the spot (for the site's coordinates).

### C2 · Credits page — branch `chaubey/credits-page`
The sample photos come from Wikimedia Commons and their licences require us to credit the authors.
- **Your files:** `web/scripts/gen-credits.mjs` (new), `web/lib/credits.ts` (generated), `web/app/credits/page.tsx` (new). Don't touch anything else.
- **Step 1, the script** (`web/scripts/gen-credits.mjs`, plain Node, no packages): read `../backend/samples/public/CREDITS.md`, take every table row that starts with `| File:`, split it on ` | `, strip HTML tags from the Author cell (`.replace(/<[^>]+>/g, "")`), and write `web/lib/credits.ts` like:
  ```ts
  export type Credit = { file: string; author: string; license: string; source: string };
  export const CREDITS: Credit[] = [
    { file: "Tree Sapling in British Columbia, Canada 2019.jpg", author: "Ben Hemmings", license: "CC BY-SA 4.0", source: "https://commons.wikimedia.org/wiki/File:..." },
    // ...
  ];
  ```
  Remove the `File:` prefix from the file name. Run it with `cd web && node scripts/gen-credits.mjs` and **commit the generated `lib/credits.ts`** too.
- **Step 2, the page** (`web/app/credits/page.tsx`): `"use client"` is not even needed here (no data fetching). Title "Image credits", one sentence ("Demo photos are from Wikimedia Commons, used under their licences."), then a `Table` from `@/components/ui/table` with columns File, Author, License, Source (the source is a link that opens in a new tab).
- **Done when:** http://localhost:3000/credits shows all 69 rows, the sidebar "Credits" link works, `pnpm lint && pnpm build` pass.
- **Target:** PR by 29 Sep 14:00.

### C3 · README draft — branch `chaubey/readme-draft`
- **Your file:** `docs/readme-draft.md` (new). Monis turns it into the real `README.md` (M11), so don't create `README.md` yourself.
- Write these sections in plain English. Use your AI tool and read `docs/project-brief.md`, `docs/01-hld.md` §3 and `docs/04-roadmap.md` §2:
  1. **One-line pitch** of FieldProof.
  2. **The problem** (3–4 sentences): NGOs and community groups need proof that their field work (planting, clean-ups, repairs) happened and made a difference.
  3. **Features** as a table: feature | what it does. Use the "IN" list from roadmap §2.
  4. **How we keep numbers honest:** the AI text is never allowed to write a number itself; it can only use placeholders that are filled from our measured data, otherwise a fixed template is used.
  5. **Privacy:** faces are blurred in shared images, GPS is rounded to 3 decimals in the API, uploads need a consent tick.
  6. **Honesty notes:** green cover % is an estimate from colour, not a scientific measurement; the demo before/after pair's date was adjusted because we only had one day.
  7. **Roadmap (not built yet):** the "OUT" list from roadmap §2.
  8. **Team:** Monis, Ujjwal, Chaubey, Aditya (+ roles).
- **Target:** PR by 29 Sep 18:00.

---

## 6. Aditya — search page, testing, screenshots

### A1 · Search page — branch `aditya/search-page`
- **Your file:** `web/app/search/page.tsx` (new). Nothing else.
- **What the page does** (roadmap T22):
  1. `"use client"`. A text box + a "Search" button. Pressing Enter also searches.
  2. Filters: a **project** select (load options from `GET /api/projects` → `{ items: Project[] }`), a **site** select that appears once a project is picked (`GET /api/projects/{id}/sites` → `{ items: Site[] }`), and a **tag** text input. All optional.
  3. Four example chips under the box: "saplings being planted", "flooded road", "solar panels", "children in a classroom". Clicking one fills the box and searches.
  4. Search call:
     ```ts
     const res = await api<{ items: SearchHit[] }>("/api/search", {
       method: "POST",
       body: JSON.stringify({ query, project_id, site_id, tag, limit: 24 }), // leave out filters that are empty
     });
     ```
  5. Results in a grid: each card is `<img src={hit.asset.thumb_url} />`, the site name, the top 3 tags as `Badge`s, and a score badge (`Math.round(hit.score * 100)`), linking to `/assets/{hit.asset.id}`.
     If `web/components/asset-grid.tsx` (from Ujjwal) is already on `master` when you start, you may use it; **otherwise just write the grid inside your page.** Don't wait for it.
  6. States: "Searching…" skeletons, "No matches" when empty, a toast on error.
- **Done when:** "solar panels" returns solar-panel photos near the top, `pnpm lint && pnpm build` pass. Screenshot in the PR.
- **Target:** PR by 29 Sep 15:00.

### A2 · Test everything (no coding) — 29 Sep, 17:00–20:00
Open the app (local with the shared API URL, or the Vercel URL once Monis shares it) and go through this list, **on a laptop and on a phone**. For each problem, open a **GitHub issue** with: page URL, what you did, what happened, what you expected, a screenshot.
- [ ] Dashboard loads, "New project" works
- [ ] Project page: add a site, sites table updates
- [ ] Upload 2 photos from a phone: they go `pending → ready`
- [ ] Library: filters by site, tag and status work; "Load more" works
- [ ] Asset page: add/remove a tag, move to another site, Lineage drawer opens
- [ ] Search: the 4 example chips give sensible results
- [ ] Compare: pair suggestions show; "Use this pair" creates a comparison; the slider and mask toggle work
- [ ] Report: create one from the project page; it becomes ready; the print page looks right (Ctrl+P preview); campaign-kit images load
- [ ] Credits page lists the photos
- [ ] Nothing is broken on a phone-sized screen (sidebar, tables, images)

### A3 · Submission screenshots — 29 Sep night / 30 Sep morning
From the **Vercel URL**, take clean full-window screenshots (no dev tools, browser zoom 100%) of: dashboard, library, asset detail with the Lineage drawer open, search results, comparison slider, comparison with the green mask, report page, print preview, campaign kit. Put them in a shared Drive folder and send Monis the link.

### A4 · Demo video helper — 29 Sep night
Help Monis record H6: read the script in `docs/05-deployment-and-submission.md` §4 (skip the map and timeline parts), click through the app while Monis narrates (or the other way round), and check the video is ≤ 3 minutes.

---

## 7. File ownership (prevents merge conflicts)

| Files | Owner |
|---|---|
| `backend/**`, `deploy/**`, `docs/04-roadmap.md`, `README.md`, `web/eslint.config.mjs`, `web/package.json`, `web/lib/api.ts`, `web/lib/types.ts` | Monis |
| `web/components/{asset-card,asset-grid,tag-chips,status-badge,lineage-panel}.tsx`, `web/app/projects/[id]/library/**`, `web/app/assets/**`, `web/app/sites/**`, `web/app/comparisons/**`, `web/app/reports/**`, print CSS in `web/app/globals.css`, the `no-print` class in `web/components/app-shell.tsx` | Ujjwal |
| `web/scripts/gen-credits.mjs`, `web/lib/credits.ts`, `web/app/credits/**`, `docs/readme-draft.md` | Chaubey |
| `web/app/search/**` | Aditya |

Anything not in this table: ask Monis before editing it.

---

## 8. Timeline

| When | What |
|---|---|
| **Mon 28 Sep, night** | Monis: M1, M2. Ujjwal: U1 PR. Chaubey/Aditya: set up the repo, `pnpm dev` working, start C2 / A1 |
| **Tue 29 Sep, 10:00** | Chaubey: C1 photos sent to Monis |
| 29 Sep, 14:00–15:00 | PRs in: C2 (credits), A1 (search), U2, U3 |
| 29 Sep, afternoon | Monis: T16 demo data, Azure deploy, Vercel |
| 29 Sep, 17:00–20:00 | U4 + C3 PRs in. Aditya: A2 testing → issues. Everyone fixes the issues on their own pages |
| **29 Sep, 20:00** | 🔒 **Feature freeze.** `DEMO_MODE=true` |
| 29 Sep, night | Demo video (Monis + Aditya). Screenshots (Aditya) |
| **Wed 30 Sep, 09:00–11:00** | Final README, final checks, submit. **Hard deadline 12:00** |

If you're stuck for more than 30 minutes, post in the group what you tried. Don't sit on it.

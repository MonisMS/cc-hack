# Project Brief: Code Cubicle 6.0

**Our picks:** PS1 "Scout" (General, ₹30K pool) + PS2 "FieldProof" (Cloudinary, ₹1.4L pool)
**Deadline:** 30 Sep 2026 · **Build order:** PS2 first · **Cost target:** ₹0

---

# PS1: "Scout", an AI data collector

## What they asked for
You type what data you need in plain English. The AI plans how to collect it, gathers it from permitted websites, cleans it, removes duplicates, shows it on a dashboard with sources, and lets you export it. It also keeps a history of past tasks.

## What we'll build
A web app where you type something like:
> *"Find 15 AI startups in Bengaluru hiring ML engineers, with company, role, careers page link and funding stage."*

1. **The AI makes a plan:** the columns it will fill, the searches it will run and the sites it may use. You can edit the plan, then click **Run**.
2. **It searches the web** and reads the result pages.
3. **The AI pulls out rows.** It only keeps links that actually appear on the page, so it can't invent URLs.
4. **It cleans the data.** It validates fields and merges duplicates by website domain (e.g. "Razorpay" and "Razorpay Pvt Ltd" become one row).
5. **The dashboard** shows a progress bar and a results table with search and filters. Clicking a row shows the page and snippet it came from. You can export to CSV or JSON, and a history page lets you re-run old tasks.

**Scope limits that keep it safe:**
- It focuses on lists of organisations and opportunities: companies, jobs, sponsors, events, grants.
- Each task is capped at 10–15 results.
- It skips LinkedIn, Indeed and Glassdoor, which block scrapers.

## Tech stack
| Part | Tool | Free limit |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui | — |
| Table | TanStack Table | — |
| Backend | Python + FastAPI | — |
| Web search | **Tavily** (Serper as backup) | 1,000/month; 2,500 once |
| Page reader | **Jina Reader** (`r.jina.ai/<url>`), no install | ~100 requests/min with a free key |
| AI model | **Cerebras** (main), **Groq** (backup), via LiteLLM | ~1M tokens/day; ~200K/day |
| Structured output | Pydantic + Instructor | — |
| Deduplication | Domain match + rapidfuzz | — |
| Database | Postgres on **Neon** | 0.5 GB |
| Progress updates | Frontend checks every 2 seconds (no streaming) | — |
| Hosting | Vercel (frontend), local or Render (backend) | Free |

---

# PS2: "FieldProof", turning NGO media into proof of impact

## What they asked for
Use Cloudinary to take the photos and videos NGOs collect from the field and:
- organise them by project, location and time;
- spot activities and what's visible in them;
- compare before and after;
- make the media searchable by meaning;
- generate reports and social-media-ready content;
- keep everything traceable to the original files.

## What we'll build
A web app for an NGO.
1. **Upload:** drag in photos and videos, which go to Cloudinary.
2. **Auto-organise:** each photo gets AI tags ("saplings", "volunteers", "flood"), plus its date and GPS read from the photo itself. It then appears on a **map**, on a **timeline** and under the right **project**.
3. **Smart search:** typing *"flooded road near school"* finds the right photos, even untagged ones.
4. **Before/after:** it pairs photos of the same site from different dates and shows a slider, plus a number like **"green cover +18%"** and a short AI description of what changed.
5. **Reports:** one click makes an impact report with a summary, numbers and photo evidence, which you can download.
6. **Campaign kit:** auto-cropped Instagram and story images, a quote card with text on the photo, and a before/after collage, all made by Cloudinary.
7. **Traceability:** click any output to see which original photo it came from and the exact edits applied.

## Tech stack
| Part | Tool | Free limit |
|---|---|---|
| Frontend | Same React app as Scout | — |
| Upload | **Cloudinary Upload Widget** | — |
| Media storage and edits | **Cloudinary** (smart crop `g_auto`, text overlays, side-by-side, video thumbnails) | 25 credits/month (target under 10) |
| Photo date and GPS | Cloudinary `image_metadata` | — |
| AI tags | Cloudinary auto-tagging add-on **or** local **CLIP** as fallback | Add-on limit to check; CLIP unlimited |
| Semantic search | **CLIP** via fastembed (runs on the laptop) + **pgvector** in Neon | Free |
| Before/after numbers | Python **Pillow** (green-pixel %) | Free |
| Change description and report text | Gemini Flash (free) / Cerebras | Free |
| Map | **Leaflet + OpenStreetMap** | Free |
| Backend and database | Same FastAPI + Neon as Scout | Free |

---

# Shared between both
```
cc-hack/
├─ core/        ← AI model router, job runner, database, export   (built once)
├─ scout/       ← PS1 backend                                      (Dev A)
├─ fieldproof/  ← PS2 backend                                      (Dev B)
└─ web/         ← ONE React app with two sections, shared components
```
- One backend, one database, one AI layer, one design.
- **Owners:** Dev A owns Scout, Dev B owns FieldProof. FieldProof gets priority because of its bigger prize.
- **Total cost:** ₹0.

---

# Start today
1. **Sign up (15 min):** Cloudinary, Neon, Tavily, Jina, Cerebras, Groq and Gemini (Google AI Studio). Put all the keys in one `.env` file.
2. **Dev B:** in Cloudinary, go to **Settings → Add-ons** and note the free limits for Google/AWS auto-tagging and AI Vision.
3. **Both:** take **"before" photos** of one real spot, with phone location on and the same angle each time.
4. **Set up the project:** Python backend and React frontend, one repo.

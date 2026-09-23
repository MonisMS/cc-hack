# Research Summary: Code Cubicle 6.0 (all findings, 23 Sep 2026)

## 1. The hackathon

- **The problem statements PDF** (in `problem-statements.md`):
  - **PS1**: AI Data Intelligence Platform (General).
  - **PS2**: Impact & Sustainability Media Platform (Cloudinary).
  - **PS3**: Edge Memory Platform on Qdrant Edge (General).
- **Updated official rules** (from the organisers' email):
  - Teams pick **at most 1 General PS + the Cloudinary PS**.
  - PS1 and PS3 are both General, so **PS1 + PS3 is not allowed**.
  - Prizes: **Cloudinary PS ₹1.4L** (Amazon vouchers) and a **Code Cubicle pool of ₹30K**.
  - **Deadline extended to 30 Sep.**
  - Mentors will be assigned, and teams are asked to submit early. Everyone gets a participation certificate.
- **Organiser: Geek Room.**
  - Past editions:
    - 1.0: Noida, May 2024.
    - 2.0: Microsoft Gurugram, Aug 2024.
    - 3.0: with Mastercard, Gurugram, Sep 2024. Judges came from Mastercard AI Garage, H2O.ai and Evalueserve.
    - 4.0: Microsoft Hyderabad, 2025.
    - 5.0: Microsoft Bengaluru, Sept 2025, on Unstop.
  - "20,000+ registrations" is claimed across editions.
- **6.0**:
  - It is listed on HackCulture. The grand prize is a Goa villa stay (Wayzyy), with Logitech mice for selected participants.
  - A third-party listing says submissions go through Devpost and gives prizes of $200, $65 plus IBM Cloud, and $35 plus a mouse. **This is unverified.**
- **Judging criteria found**: Innovation & Creativity, and Technical Implementation. The rest of the rubric is not public.
  - Required: a working project, a problem and solution description, a demo, a repo link and a presentation.
- **Past winners**: the only one confirmed is Team Bithub (VIT) at 5.0: 3rd overall and 1st in the Cybersecurity track, from 1,000+ teams. Their project name was not found.
- **Sponsors**: no pre-announcement listed Cloudinary or Qdrant as sponsors. The organisers' email later confirmed the Cloudinary prize.
- **A related Cloudinary contest**: "Pixels to Products AI Hackathon 2026" (HackIndia) runs 14 Sep – 3 Oct with a **₹1.4L** prize.
  - It may be the same prize pool. **This is unverified.** If it is, expect more competition.
  - A public PS2 repo named "impactlens-ai" already exists.
- **Still unconfirmed:** the offline-round date (11 Oct?), the submission platform, whether resubmission is allowed, and whether Cloudinary hackathon credits exist (see cld.media/hackathons).

## 2. PS1 tooling (free tiers and limits)

**Scraping**
| Tool | Free tier | Notes |
|---|---|---|
| Firecrawl | 1,000 credits/month | Structured JSON extraction costs 5 credits per page. `/extract` is deprecated in favour of `/agent`. |
| Crawl4AI | Open source, unlimited | Painful on Windows: Playwright install bugs (#1050, #377, #1549), async-only API, v0.8 changed the Docker server. |
| Jina Reader | ~20 requests/min without a key; 100/min and 10M tokens with a free key | No install needed. **Recommended.** |
| ScrapeGraphAI | Open-source library free; cloud has 500 credits | Invalid-JSON and context-length bugs when used with Groq. |
| Playwright | Free | — |

**Search**
| Tool | Free tier | Notes |
|---|---|---|
| Tavily | 1,000 credits/month, no card | Recommended primary. |
| Brave | **Free tier removed Feb 2026** | Now needs a card: $5 credit, then metered, with no spending cap by default. Avoid. |
| Serper | 2,500 queries, once | Recommended backup. |
| Exa | $20 at signup + $10/month | A 20k/month claim is **unverified**. |
| DuckDuckGo (ddgs) | Unofficial | Blocks you below ~30 requests/min. |
| SearXNG | Self-hosted | — |

**LLMs**
| Provider | Free tier | Notes |
|---|---|---|
| Groq (gpt-oss-120b / 20b, qwen) | 30 requests/min, 1K requests/day, **8K tokens/min, 200K tokens/day** per model, per organisation | Llama 3.3 70B is gone from the official list. Only about 1 page/min and ~30 pages/day of extraction. Strict JSON mode works only on gpt-oss models. |
| Gemini | Quotas cut 50–80% in Dec 2025; **Pro removed from the free tier on 1 Apr 2026** | Flash is roughly 10–15 requests/min and ~1,500/day (unverified). |
| OpenRouter free models | 20 requests/min; 50/day, or 1,000/day after a one-time $10 purchase | — |
| Cerebras | ~1M tokens/day, no card | Per-model limits unverified. |
| Ollama | Local, free | — |

**Hosting and database**
| Service | Free tier | Notes |
|---|---|---|
| Vercel Hobby | Non-commercial only; 300 s functions | — |
| Render | Sleeps after 15 min idle; 512 MB RAM | — |
| Railway | 30-day trial, then $1/month | — |
| Fly.io | **No free tier for new users** | — |
| Supabase | 500 MB database | Pauses after 7 days idle. |
| Neon | 0.5 GB, 100 CU-hours | Scales to zero after 5 min. |
| Upstash Redis | 256 MB, 500K commands/month | BullMQ drains it by polling. |
| Cloudflare Workers | 100K requests/day, 10 ms CPU | — |

**Job queues**: pg-boss (Postgres, Node), Inngest (50–100K runs free), or a Postgres table with SKIP LOCKED.

## 3. PS1 difficulty and gotchas

- Cloudflare now blocks AI crawlers by default (since Jul 2025).
- One benchmark found LLM agents succeed on only 5–10% of CAPTCHA sites.
- Scraping LinkedIn, Indeed or Glassdoor is banned by their terms. LinkedIn won a $500K judgment against hiQ.
- LLMs fabricate 3–13% of URLs even with retrieval.
  - **Fix**: accept a URL only if it appears in the fetched page, and check it with a HEAD request.
- Fuzzy matching on company names makes wrong merges ("Pepsi – New York" matched "New York Life").
  - **Fix**: dedupe by domain first, then by name.
- FastAPI live progress (SSE plus BackgroundTasks) has pitfalls.
  - **Fix**: have the frontend poll every 2 s.
- Existing tools don't cover dedupe, history or a dashboard.
- **Verdict**: doable if narrowed. Focus on lists of organisations and opportunities, 10–15 results per task, search with Tavily, read with Jina, extract with Cerebras/Groq plus Pydantic, then URL grounding and domain dedupe.

## 4. PS3 (Qdrant Edge) findings

- **What it is:** an embedded vector search engine inside your app, "SQLite for vectors". Private beta started 29 Jul 2025, and it is still **beta**.
- **Package:** `qdrant-edge-py` **0.8.0** (5 Aug 2026), with 11 releases since Dec 2025 and 0.9 on the way.
- **Languages and platforms:** Python and Rust only. No JavaScript, no mobile builds. Wheels exist for Linux, macOS and Windows x64.
- **Python lags Rust:** some features are missing, and the type hints were out of date (PR #10693).
- **Features:** dense, sparse and **built-in BM25** search; hybrid fusion (RRF/DBSF); filters; quantization; snapshots.
- **No background optimizer:** you must call `optimize()` manually.
- **Sync is do-it-yourself:**
  - The pattern: a full shard snapshot to start, partial snapshots via manifest for updates, and a mutable shard plus an upload queue for local writes.
  - The guide's code is 40–60 lines, **with no deletes, retries, conflict handling or persistent queue**.
  - Pitfalls: clock skew, tombstones, idempotency, duplicates across two shards.
  - Whether the free tier supports partial snapshots is **unverified**; the server needs version ≥ 1.17.
- **Qdrant Cloud free tier:** 1 GB RAM, 0.5 vCPU, 4 GB disk. Suspended after 1 week unused, deleted after 4 weeks.
- **Community:** almost none. One Rust repo with 1 star and one Medium post.
- **Fallback:** `QdrantClient(path=...)` local mode is for testing only. It warns above 20k points and allows a single process.
- **Verdict:** local search takes about 1 day, but real sync takes 3–5+ days. **High risk for beginners.**

## 5. PS2 (Cloudinary) findings

- **Free plan:**
  - 25 credits over a rolling 30 days. 1 credit = 1,000 transformations, 1 GB storage or 1 GB bandwidth.
  - Caps: images 10 MB, videos 100 MB, 25 MP.
  - **No overage: going over disables the account.**
- **Video is expensive:** SD costs 2 and HD 4 transformations per second.
- **Generative AI is expensive:** 50–230 transformations each, and availability on Free is unverified.
- **AI add-ons:**
  - Google, AWS and Imagga tagging; AI Content Analysis (`coco_v2`); AI Vision.
  - Most have free quotas, **but the exact numbers are visible only after login**.
  - Transcription and auto-chaptering availability is unverified.
- **Visual and natural-language search is Enterprise-only.** Build our own with CLIP plus pgvector.
- **Search API** is on Free, but EXIF and location search are premium-only.
- **Admin API:** 500 calls per hour on Free.
- **Tooling:** official MCP servers, agent skills, and Node, Python and Next.js SDKs.
- **Difficulty:** medium. Mature, well documented, and predictable for demos.
- **Full edge-case list:** `ps2-edge-cases.md` (121 items).

## 6. Decisions made

1. First plan: PS1 + PS3. **Voided by the updated rules.**
2. Compared the options: **PS3 is the most complex and error-prone.** PS1 (narrowed) and PS2 are safer.
3. **Final choice: PS1 "Scout" + PS2 "FieldProof", building PS2 first** because of the ₹1.4L prize. Everything uses free tiers, for ₹0 total.
4. **Stack:**
   - Frontend: React + Vite + TypeScript + Tailwind + shadcn.
   - Backend: FastAPI.
   - Database: Neon Postgres + pgvector.
   - LLMs: LiteLLM routing to Cerebras, Groq and Gemini.
   - PS1: Tavily + Jina.
   - PS2: Cloudinary + CLIP (fastembed) + Pillow + Leaflet.
5. **One shared core** (LLM router, jobs, database, export) and one React app for both products.

## 7. Files in this repo

| File | Contents |
|---|---|
| `problem-statements.md` | Text of the problem-statements PDF |
| `strategy.md` | v2 strategy: scoring, MVPs, day plan, demo scripts, risks, cost |
| `project-brief.md` | What we're building and the tech stack for PS1 and PS2 |
| `ps2-edge-cases.md` | 121 PS2 edge cases, a day-1 checklist, the top 10, and sources |
| `research-summary.md` | This file |

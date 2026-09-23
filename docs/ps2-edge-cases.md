# FieldProof (PS2): Edge Cases, Errors & Gotchas

_Researched 23 Sep 2026. The list is ordered by build phase, from setup to demo day. Each item reads **Problem**, then **Symptom**, then **Fix**._
_Items marked **(unverified)** come from community reports or inference. Test those yourself early._

---

## 0. Day-1 checklist (do these first; each one removes a whole class of problems)

- [ ] **Cloudinary Console → Settings → Add-ons:**
  - Register the free tiers of Google Auto Tagging, AWS Rekognition, Imagga and Cloudinary AI Content Analysis.
  - **Write down each free quota.** You can't see these anywhere without logging in.
- [ ] **Cloudinary Console → Settings → Upload → create an UNSIGNED preset** containing:
  - `media_metadata: true`
  - `categorization` / `detection` + `auto_tagging`
  - allowed formats, max file size, and an incoming `c_limit,w_4000`
- [ ] **Cloudinary Console → Settings → Security:** enable "Allow delivery of PDF and ZIP files" if the reports will be PDFs.
- [ ] **Check the folder mode** (dynamic vs fixed); see #20.
- [ ] **Neon:** run `CREATE EXTENSION IF NOT EXISTS vector;` on the **direct** (non-pooler) connection string.
- [ ] **Download the CLIP models** (~600 MB) into `./models` and back them up to a USB stick.
- [ ] **Check Gemini's free limits** in AI Studio. The numbers change without notice.
- [ ] **Keep the repo in the WSL Linux filesystem** (`~/cc-hack`), not under `/mnt/c`.
- [ ] **Add `.env` to `.gitignore` before the first commit.**
- [ ] **Take the "before" photos** straight from the phone camera with location ON. Don't send them via WhatsApp.

---

## 1. Environment & project setup

1. **Repo under `/mnt/c` in WSL**
   - Symptom: pip, npm and Vite are painfully slow, and hot reload misses changes.
   - Fix: keep the repo in `~/`. If it has to stay on `/mnt/c`, set Vite `server.watch.usePolling: true`.
2. **WSL networking**
   - Symptom: a Windows browser or a phone can't reach the app.
   - Fix: run `uvicorn --host 0.0.0.0` and `vite --host`. Use `127.0.0.1`, not `::1`. Allow the port through the Windows firewall. On Windows 11, consider `networkingMode=mirrored` in `.wslconfig`.
3. **CRLF line endings**
   - Symptom: `/bin/bash^M: bad interpreter`, or `.env` values end with a stray `\r`.
   - Fix: run `git config core.autocrlf input` and add a `.gitattributes` containing `* text=auto eol=lf`.
4. **onnxruntime DLL error on native Windows**
   - Symptom: `DLL load failed while importing onnxruntime_pybind11_state`.
   - Fix: run the backend inside WSL2, or install the VC++ Redistributable. Never install `onnxruntime` and `onnxruntime-gpu` together.
5. **`.env` not loaded**
   - Symptom: `KeyError` or `None` when reading an API key.
   - Fix: call `load_dotenv()` before reading env vars, or use pydantic-settings. Commit a `.env.example`.
6. **Secrets committed to git**
   - Symptom: leaked keys on GitHub.
   - Fix: gitignore `.env` from the very first commit, and rotate any key that was ever pushed.
7. **`VITE_*` variables are public**
   - Symptom: `VITE_CLOUDINARY_API_SECRET` or the Gemini key shows up in the JS bundle.
   - Fix: the frontend gets only the backend URL, the Cloudinary `cloud_name` and the unsigned preset name. Every secret stays in FastAPI.
8. **Python SDK returns `http://` URLs**
   - Symptom: mixed-content warnings.
   - Fix: `cloudinary.config(secure=True)`, or use `CLOUDINARY_URL`.
9. **Missing `python-multipart`**
   - Symptom: `Form data requires "python-multipart"`.
   - Fix: `pip install python-multipart`. Not `multipart`, which is a different package. Add it to `requirements.txt`.

## 2. Upload (Cloudinary Upload Widget + unsigned preset)

10. **Widget script not loaded yet**
    - Symptom: `window.cloudinary is undefined`.
    - Fix: put `<script src="https://upload-widget.cloudinary.com/latest/global/all.js">` in `index.html`, or wait for the script's `onload`.
11. **React StrictMode double-mount**
    - Symptom: two widgets open, or the success callback fires twice, which creates duplicate DB rows.
    - Fix: keep the widget in a `useRef`, create it only once, and call `widget.destroy()` in cleanup. Or create it inside the click handler. Also make the DB insert idempotent on `public_id`.
12. **Widget option casing**
    - Symptom: options are silently ignored.
    - Fix: the widget uses camelCase (`cloudName`, `uploadPreset`, `maxFiles`, `clientAllowedFormats`). The Python SDK uses snake_case.
13. **Preset is "Signed"**
    - Symptom: `Upload preset must be whitelisted for unsigned uploads`.
    - Fix: set the preset's Signing mode to Unsigned. The preset name is case-sensitive.
14. **Wrong preset or cloud name**
    - Symptom: `Upload preset not found`.
    - Fix: read the `X-Cld-Error` header or the error body, and check the preset exists in *this* environment.
15. **Unsigned uploads reject most parameters**
    - Symptom: `<X> parameter is not allowed when using unsigned upload`.
    - Fix: put `media_metadata`, `categorization`, `detection`, `auto_tagging`, `eager`, `eager_async`, `notification_url` and `auto_transcription` **inside the preset**.
16. **The preset overrides the request**
    - Symptom: the `folder` or `public_id` you pass is ignored.
    - Fix: for unsigned uploads, single-value settings in the preset win. Tags, context and metadata get merged.
17. **Re-upload returns the old asset**
    - Symptom: an unsigned upload to an existing `public_id` returns `"existing": true`, which looks like a success.
    - Fix: check `existing`, or let Cloudinary generate unique IDs.
18. **Unsigned preset name is a public write key**
    - Symptom: anyone can upload to your account and burn credits.
    - Fix: restrict formats and size in the preset, and rotate the preset name if it's abused. Say "signed uploads in production" to the judges.
19. **Free-plan size caps**
    - Symptom: `File size too large`.
    - Limits: image 10 MB, video 100 MB, 25 MP per image. 4K phone video hits 100 MB in about 15–20 s.
    - Fix: set `maxImageFileSize`/`maxVideoFileSize` in the widget, record at 1080p, keep clips short.
20. **Dynamic vs fixed folders**
    - Symptom: in dynamic mode, `asset_folder` doesn't appear in the URL. In fixed mode, moving an asset breaks its links.
    - Fix: check the mode on day 1. Store the `public_id` and `secure_url` from the upload result and never rebuild them.
21. **48/50 MP phone photos**
    - Symptom: `Maximum image size is <n> Megapixels`. Whether this hits at upload time is **unverified**.
    - Fix: add an incoming transformation `c_limit,w_4000` to the preset.
22. **iPhone HEIC**
    - Symptom: the upload works, but the `.heic` `secure_url` shows as a broken image in Chrome and Firefox.
    - Fix: always deliver with `f_auto` or `f_jpg`. If Pillow reads the original, also `pip install pillow-heif` and call `register_heif_opener()`.
23. **`public_id` rules**
    - Symptom: invalid IDs or mangled names.
    - Rules: max 255 chars; no `? & # \ % < > +`; no leading or trailing `/`.
    - Fix: slugify the IDs.
24. **Short underscore folder names**
    - Symptom: a folder like `u_2/` or `ab_x/` is parsed as a transformation, giving `Invalid transformation parameter`.
    - Fix: use hyphens in folder names.
25. **Bulk upload bursts**
    - Symptom: `HTTP 420 Rate limited`, or timeouts on field networks.
    - Fix: widget `maxFiles: 20`. The widget chunks uploads automatically. In Python, use `upload_large`, with ~10 concurrent uploads and backoff on 420.
26. **Wrong `resource_type` in Python**
    - Symptom: video uploads fail as `Invalid image file`.
    - Fix: pass `resource_type="auto"`.
27. **Python `async` keyword**
    - Symptom: passing `async=True` raises a `SyntaxError`.
    - Fix: use `**{"async": True}`.

## 3. Metadata: date, GPS, orientation

28. **The parameter was renamed but the response key wasn't**
    - Symptom: `image_metadata` is empty or deprecated.
    - Fix: send `media_metadata: true` in the preset, and read `result["image_metadata"]`.
29. **GPS comes back as text**
    - Symptom: `"37 deg 33' 49.66\" N"`, not decimals.
    - Fix: write a DMS → decimal parser that negates for S and W, and unit-test it.
30. **Pillow reads GPS from the wrong place**
    - Symptom: `getexif()[34853]` returns an int.
    - Fix: use `img.getexif().get_ifd(0x8825)`, then `float()` each rational value.
31. **Browsers strip GPS**
    - Symptom: iOS Safari and Android Chrome file pickers remove the location before upload.
    - Fix: capture `navigator.geolocation` at upload time as a fallback. Store `provenance: exif | device | manual`.
32. **WhatsApp, Instagram and screenshots have no EXIF**
    - Symptom: no date or GPS on most "real" NGO photos.
    - Fix: EXIF is optional evidence. Add a manual "pin on map" and a date picker. Tell field staff to send photos "as document".
33. **Transformed copies lose EXIF**
    - Symptom: EXIF read from a derived URL is empty.
    - Fix: read metadata only from the **upload response** (or `explicit`), and save it to the DB immediately.
34. **0,0 "Null Island" or out-of-country coordinates**
    - Symptom: markers appear in the Gulf of Guinea.
    - Fix: treat `(0,0)`, `None` and anything outside the country's bounding box as "no location".
35. **`DateTimeOriginal` has no timezone and uses colons**
    - Symptom: `"2026:09:21 14:03:11"` sorts wrong.
    - Fix: parse with `%Y:%m:%d %H:%M:%S` and use `OffsetTimeOriginal` if present. Otherwise assume Asia/Kolkata and set a flag.
36. **Wrong phone clock**
    - Symptom: the "after" photo is dated before the "before" photo, or the year shows as 2000.
    - Fix: reject dates in the future or before the project start. Fall back to upload time and let the user override.
37. **EXIF orientation**
    - Symptom: photos come out sideways in Pillow and before/after pairs are misaligned. Cloudinary auto-rotates on delivery, but Pillow doesn't.
    - Fix: call `ImageOps.exif_transpose(img)` first. Don't hard-code portrait/landscape from the raw width and height.

## 4. AI tagging (Cloudinary add-ons + CLIP fallback)

38. **Add-on not registered**
    - Symptom: tagging calls fail.
    - Fix: Console → Add-ons → install the Free tier before using it.
39. **Add-on quota is a hard stop**
    - Symptom: `Limit of <n> <add-on> operations reached`.
    - Fix: budget your test uploads. If there are no tags, fall back to CLIP zero-shot automatically.
40. **`detection` needs a model name**
    - Symptom: a wrong model name gives no result, and results never become tags.
    - Fix: use `detection: "coco_v2"` (or lvis, unidet…) **plus** `auto_tagging: 0.6`. Results are in `info.detection.object_detection.data`.
41. **`categorization` without `auto_tagging`**
    - Symptom: results appear only in `info`, never as tags.
    - Fix: always pair `categorization: "google_tagging"` with `auto_tagging: 0.x`.
42. **Async results**
    - Symptom: the response shows `"status": "pending"`.
    - Fix: poll `cloudinary.api.resource()` from the backend, gently (see #62), or use `notification_url`.
43. **Webhooks can't reach localhost**
    - Symptom: `notification_url` never fires.
    - Fix: use cloudflared or ngrok (free), return 200 fast, and verify `X-Cld-Signature`. Or avoid webhooks entirely by polling.
44. **Bare CLIP labels tag poorly**
    - Symptom: zero-shot tags are poor.
    - Fix: use the template "a photo of a {label}." and average several templates.
45. **CLIP always picks something**
    - Symptom: every image gets a tag, even a wrong one. Scores sit in the narrow 0.2–0.35 range **(unverified)**.
    - Fix: add "other" or negative labels. Calibrate per-tag thresholds on 20–30 hand-labelled photos, and show the output as "suggested tags".
46. **CLIP can't count or read text**
    - Symptom: "50 saplings" or signboard text is wrong.
    - Fix: never derive numbers from CLIP. Use it only for search and coarse tags.

## 5. Semantic search (fastembed CLIP + pgvector on Neon)

47. **First-run model download of ~600 MB**
    - Symptom: startup appears to hang. The vision model is 352 MB and the text model 254 MB.
    - Fix: pre-download both on day 1 and pass `cache_dir="./models"` (gitignored).
48. **Default cache is in /tmp**
    - Symptom: models re-download after a reboot.
    - Fix: set `FASTEMBED_CACHE_PATH` or `cache_dir`.
49. **Hangs offline even when cached**
    - Symptom: venue Wi-Fi is down and startup freezes, because fastembed contacts Hugging Face first.
    - Fix: set `HF_HUB_OFFLINE=1` or `local_files_only=True`, and **test it with Wi-Fi off**.
50. **Image mode errors**
    - Symptom: RGBA PNGs, palette, grayscale or CMYK images crash or give wrong colours.
    - Fix: always run `exif_transpose(...)` then `.convert("RGB")` before embedding.
51. **Huge images**
    - Symptom: `DecompressionBombError` or a RAM spike.
    - Fix: `img.thumbnail((1024,1024))` first. Or fetch a Cloudinary `w_1024` version for analysis instead of the original.
52. **Slow CPU inference**
    - Symptom: roughly 50–200 ms per image after warm-up **(unverified; benchmark it)**, and the first call is slow.
    - Fix: load the models once at startup (FastAPI lifespan), embed in batches, and store the vectors so nothing is re-embedded.
53. **Mismatched models**
    - Symptom: search returns garbage.
    - Fix: use exactly `Qdrant/clip-ViT-B-32-vision` and `-text` (512-d, shared space). Hard-code `VECTOR(512)` and assert `len==512` before insert.
54. **Normalisation**
    - Symptom: rankings look strange.
    - Fix: L2-normalise the vectors yourself **(unverified whether fastembed does it)** and use cosine distance `<=>`.
55. **pgvector extension missing**
    - Symptom: `type "vector" does not exist`.
    - Fix: `CREATE EXTENSION vector;` on the direct URL.
56. **Vectors come back as strings**
    - Symptom: `can't adapt type numpy.ndarray`, or values return as `'[0.1,...]'` text.
    - Fix: `pgvector.psycopg.register_vector(conn)` on **every** pooled connection, or `pgvector.sqlalchemy.VECTOR`.
57. **IVFFlat on an empty table**
    - Symptom: low recall; obvious matches are missed.
    - Fix: use **HNSW** with `vector_cosine_ops`. Below 10k rows, no index is needed at all.
58. **Operator doesn't match the index**
    - Symptom: the index isn't used.
    - Fix: `ORDER BY embedding <=> :q` goes with `vector_cosine_ops`. Similarity = `1 - distance`.
59. **Neon pooler and prepared statements**
    - Symptom: `prepared statement "_pg3_0" does not exist`.
    - Fix: psycopg `prepare_threshold=None`, or asyncpg `statement_cache_size=0`. Run migrations on the direct URL.
60. **Neon cold start after 5 minutes idle**
    - Symptom: the first request is slow or fails with `SSL SYSCALL error: EOF`.
    - Fix: `pool_pre_ping=True`, `pool_recycle=300`, `connect_timeout=10`, one retry, and hit `/health` before the demo.
61. **0.5 GB storage cap**
    - Symptom: writes fail.
    - Fix: store only URLs, metadata and vectors (~2 KB per row). **Never store image bytes in Postgres.**
62. **Cloudinary Admin API is limited to 500 calls/hour on Free**
    - Symptom: `420`. Search, `resource()` and metadata calls all count toward it.
    - Fix: your own DB is the source of truth. Don't list or search Cloudinary in loops.
63. **Cloudinary Search API limits**
    - Symptom: searching by EXIF or `location:` fails; those are premium-only. New uploads may also not be searchable immediately **(unverified)**.
    - Fix: copy GPS and date into your own DB and query there.
64. **Queries in Hindi or Hinglish**
    - Symptom: random results, because CLIP is English-only.
    - Fix: translate the query to English with one LLM call, or state that search is English-only.

## 6. Organising: projects, sites, map, timeline

65. **Structured metadata fields must exist first**
    - Symptom: writes fail.
    - Fix: a one-time script creates the fields (`project`, `site`, `phase`) with snake_case `external_id`s. Enum values use datasource external IDs. Max 100 fields.
66. **Writing metadata**
    - Symptom: `|` or `=` inside values breaks the `key=value|key2=value2` format **(unverified)**.
    - Fix: write from FastAPI after upload with `cloudinary.uploader.update_metadata(...)`.
67. **Leaflet marker icons missing in Vite**
    - Symptom: broken-image markers.
    - Fix: import the icon PNGs from `leaflet/dist/images` and `L.Icon.Default.mergeOptions(...)`, or use `L.divIcon`.
68. **Grey or blank map**
    - Symptom: grey tiles or an empty box.
    - Fix: `import 'leaflet/dist/leaflet.css'` and give the container an explicit height. If the map is in a hidden tab, call `map.invalidateSize()` when it's shown.
69. **react-leaflet version mismatch**
    - Symptom: peer-dependency errors.
    - Fix: v5 needs React 19 and v4 needs React 18. Don't use `--force`.
70. **OSM tile policy**
    - Symptom: `403` tiles.
    - Fix: keep the attribution, don't bulk-prefetch tiles, and don't strip the Referer.
71. **Location privacy**
    - Symptom: exact GPS of homes, schools or children is exposed.
    - Fix: show site-level locations only (round to ~3 decimals ≈ 100 m), and never put raw EXIF in public reports.

## 7. Before/after comparison & green-cover metric

72. **Different framing**
    - Symptom: a fake "+40%" that is really just a camera-angle change.
    - Fix: give both images the same Cloudinary crop (`c_fill,w_800,h_600`) and resize to identical dimensions. Show a "framing mismatch" warning when CLIP similarity between the pair is low.
73. **Lighting and white balance**
    - Symptom: ±15–30% swing between morning and noon photos.
    - Fix: normalise the colour channels (r=R/(R+G+B)…), use an Otsu threshold, and mask very dark and very bright pixels.
74. **Sky, green walls or tarps**
    - Symptom: green cover is overcounted.
    - Fix: use a lower region of interest or a user-drawn crop, and **show the green-mask overlay** so judges can see what was counted.
75. **False precision**
    - Symptom: "23.47% increase" looks fake.
    - Fix: round to 5% or show a range, and label it "estimated / indicative".
76. **Satellite pairs**
    - Symptom: season, clouds and sensor differences dominate the signal.
    - Fix: compare the same month in different years, and show the image dates.
77. **Slider issues**
    - Symptom: a home-made slider breaks on touch or mismatched sizes.
    - Fix: use `react-compare-slider` and feed both images through the same crop URL.
78. **Tainted canvas**
    - Symptom: `Tainted canvases may not be exported` when reading pixels in the browser.
    - Fix: set `crossOrigin="anonymous"` **before** `src`. Better: do the pixel maths in Python.

## 8. Cloudinary transformations (campaign kit, collage, keyframes)

79. **Overlay IDs use colons**
    - Symptom: `l_sites/abc/before` gives a 404.
    - Fix: use `l_sites:abc:before` followed by `fl_layer_apply`.
80. **Special characters in `l_text`**
    - Symptom: a comma breaks the URL.
    - Fix: double-encode `,` `/` `%` (e.g. `%252C`), or build the URL with the SDK.
81. **Emoji in `l_text`**
    - Symptom: `Invalid encoding` or `Failed rendering text`.
    - Fix: overlay an emoji PNG image instead.
82. **Custom fonts**
    - Symptom: the font isn't found.
    - Fix: upload as raw + `type=authenticated` with the extension in the `public_id`, and no underscores in the path. Or stick to built-in fonts (Arial, Roboto…).
83. **`g_auto` with the wrong crop mode**
    - Symptom: `Auto gravity can only be used with crop, fill, thumb, lfill`.
    - Fix: use `c_fill,g_auto`.
84. **Debugging broken transformation URLs**
    - Symptom: just a 400 or 404.
    - Fix: run `curl -I <url>` and read the `X-Cld-Error` header, which names the bad parameter.
85. **Video too large for on-the-fly transformation**
    - Symptom: `Video is too large to process synchronously` (~40 MB on Free).
    - Fix: put keyframe and crop transformations in the preset as `eager` + `eager_async: true`.
86. **Long videos return `423 Locked` while processing**
    - Fix: pre-generate eagerly, and retry after the job completes.
87. **Keyframes past the video's end**
    - Symptom: `so_` beyond the duration probably errors **(unverified)**.
    - Fix: clamp `so_` to the `duration` from the upload result. Use a `.jpg` extension on the video URL.
88. **Generative AI is expensive**
    - Cost: gen_remove / gen_fill = 50, gen_replace = 120, gen_background_replace = 230 transformations each. Availability on Free is **unverified**.
    - Fix: use it once, maybe, and reuse the same URL; repeat views are free.
89. **Random transformation variants burn credits**
    - Fix: use a fixed set of named transformations (thumb, card, square, story).
90. **Strict transformations**
    - Symptom: turning it on breaks dynamic `l_text` URLs.
    - Fix: leave it off for the hackathon, and mention signed URLs as the production plan.

## 9. LLM: change descriptions & report text

91. **Gemini free limits change without notice** (Pro was removed from the free tier on 1 Apr 2026)
    - Symptom: `429` on demo day.
    - Fix: re-check AI Studio limits on day 1 and demo day. **Cache every generated text in the DB.**
92. **Free Gemini data may be used for training and human review**
    - Symptom: a privacy problem for beneficiary photos.
    - Fix: send face-blurred derivatives (`e_blur_faces`) or text-only metrics.
93. **LiteLLM model naming**
    - Symptom: it asks for Vertex/GCP credentials.
    - Fix: use the prefixes `gemini/…`, `groq/…` and `cerebras/…` with the matching `*_API_KEY`.
94. **Hallucinated numbers**
    - Symptom: the report says "500 trees planted", which nobody measured.
    - Fix: pass the computed metrics as JSON, keep the numbers in a template, and let the LLM write only the prose. Check in code that every number in the output exists in the input.
95. **Broken JSON output**
    - Symptom: markdown fences or truncated output.
    - Fix: use `response_format` with a Pydantic schema, strip the fences, and retry once.
96. **Uncaught 429s**
    - Symptom: the UI shows a 500 error.
    - Fix: `num_retries=3` and a router fallback (Gemini → Groq → Cerebras). Show "description pending".
97. **Fallback model rejects images**
    - Symptom: Groq or Cerebras text models error on image input.
    - Fix: make the fallback text-only, driven by metrics and tags.
98. **Large images sent to the LLM**
    - Symptom: slow or rejected requests.
    - Fix: send a 1024 px `w_1024,q_auto,f_jpg` Cloudinary URL.

## 10. Backend (FastAPI)

99. **CORS**
    - Symptom: `No 'Access-Control-Allow-Origin'`.
    - Fix: list the exact origins (`http://localhost:5173`, `http://127.0.0.1:5173`, the Vercel URL). Don't combine `*` with credentials. **A server 500 also shows up as a CORS error**, so check the server logs first.
100. **Calling the Cloudinary Admin API from React**
     - Symptom: a CORS error, and it would need the secret anyway.
     - Fix: proxy all list, search, usage, delete and metadata calls through FastAPI.
101. **Blocking CPU work in `async def`**
     - Symptom: the whole server freezes during CLIP or Pillow work.
     - Fix: use plain `def` endpoints or `run_in_threadpool`, and `litellm.acompletion` inside async code.
102. **BackgroundTasks aren't a queue**
     - Symptom: jobs are lost on reload.
     - Fix: a `status` column (pending, processing, done, failed) that the frontend polls, plus a "reprocess pending" endpoint.
103. **No upload size limit**
     - Symptom: a big file eats RAM.
     - Fix: reject anything over ~15 MB. Most uploads go browser → Cloudinary directly anyway.
104. **Duplicate callbacks create duplicate rows**
     - Fix: a UNIQUE constraint on `public_id`, and upsert.

## 11. Reports & export

105. **PDF delivery blocked on new Free accounts**
     - Symptom: `401 … restricted`.
     - Fix: Settings → Security → allow PDF/ZIP delivery. Or generate the PDF in the browser.
106. **Print-to-PDF styling**
     - Symptom: backgrounds vanish, cards split across pages, the map prints grey.
     - Fix: `print-color-adjust: exact`, `break-inside: avoid`, `@page { size: A4 }`, and hide the navigation. For the map, use a static snapshot image.
107. **Large gallery performance**
     - Symptom: 200 full-size images lag.
     - Fix: thumbnails via `w_300,c_fill,q_auto,f_auto`, `loading="lazy"`, and fixed aspect-ratio boxes.
108. **Traceability links break**
     - Fix: store `public_id`, `version`, `asset_id`, the exact derived `secure_url`, the model name and a timestamp for every output. Keep `v<version>` in URLs.

## 12. Deletion & cache

109. **`destroy` defaults to images**
     - Symptom: deleting a video returns `"not found"`.
     - Fix: pass `resource_type="video"`, or `"raw"` (with the extension) for transcripts.
110. **Deleted files are still served**
     - Fix: pass `invalidate=True`; propagation takes minutes. Deletes are permanent unless backups are enabled. The limit is 100 IDs per call.

## 13. Credits & quotas

111. **Going over 25 credits**
     - Symptom: warnings, then the **account is disabled**: uploads and new transformations are blocked. There are no overages. The window is a rolling 30 days, not a monthly reset.
     - Fix: check the usage dashboard daily and add a `cloudinary.api.usage()` → `credits.used_percent` widget. Stay under about 10 credits.
112. **Video eats credits**
     - Cost: HD = 4 transformations/sec; 1 credit ≈ 250 HD seconds.
     - Fix: use 3–5 SD clips of 20–30 s each.
113. **Neon has 100 CU-hours a month; Gemini's daily limits reset each day**
     - Fix: pause heavy testing near the demo, and keep a separate "demo" Gemini key.

## 14. Deployment

114. **Render free tier: 512 MB RAM, sleeps after 15 min**
     - Symptom: the CLIP models (~600 MB) crash it with out-of-memory, and cold starts take about a minute. The out-of-memory part is inferred **(unverified)**, but very likely.
     - Fix: **run the backend locally for the demo.** Render is only a "live link" without CLIP, or with the text model only.
115. **Vercel SPA returns 404 on refresh**
     - Fix: add `vercel.json` with a rewrite of `/(.*)` → `/index.html`.
116. **Changing Vercel env vars**
     - Symptom: the new value doesn't apply, because `VITE_*` is inlined at build time.
     - Fix: redeploy after every env change.
117. **Mixed content**
     - Symptom: the HTTPS Vercel site can't call `http://localhost`.
     - Fix: run the frontend locally too, or expose the backend through an HTTPS cloudflared/ngrok tunnel.

## 15. Demo day & competition

118. **Venue Wi-Fi fails**
     - Fix: models pre-cached with `HF_HUB_OFFLINE=1`; all embeddings, metrics and LLM texts precomputed in the DB; a "demo mode" that reads cached results; a phone hotspot; and a **backup video**.
119. **Credits run out on the day**
     - Fix: check Cloudinary usage the day before, and use only the fixed transformation set.
120. **Dataset licensing**
     - Rules: NASA imagery is mostly public domain, but the NASA logo is not and you can't imply endorsement. Wikimedia images are usually CC BY/BY-SA and need **TASL** attribution (Title, Author, Source, License).
     - Fix: a Credits page, and no NASA logo on the slides.
121. **Consent for people in photos**
     - Fix: use your own or public-domain photos, blur faces by default (`e_blur_faces` / `e_pixelate_faces`), and add a consent checkbox per upload. **Pitch this to the judges as a feature.**

---

## Top 10 most likely to bite (in order)
1. Render's 512 MB limit can't hold the CLIP models, so **demo from a local backend** (#114).
2. Photos arrive with no GPS or date (WhatsApp, browser stripping, transformed copies), so **manual pin + browser geolocation fallback, and read metadata only from the upload response** (#31–33).
3. Unsigned uploads reject the AI and metadata parameters, so **put them in the preset** (#15).
4. Add-on quotas are unknown or tiny, so **check on day 1 and use CLIP as the fallback** (#38–39).
5. Models download or hang at the venue, so **pre-cache them and set `HF_HUB_OFFLINE=1`** (#47–49).
6. Server freezes from CLIP running in `async def`, so **use plain `def` or a threadpool** (#101).
7. Leaflet icons and map height break (#67–68).
8. CORS and mixed content (#99, #117).
9. Green-cover % fooled by framing or lighting, so **same crop, mask overlay, "estimated" label** (#72–75).
10. Credits or Gemini quota run out near the demo, so **cache everything and use fixed transformations** (#91, #111).

## Test these early (unverified)
- CLIP CPU speed per image.
- Whether fastembed normalises its vectors.
- CLIP score range and thresholds.
- Whether Render actually runs out of memory.
- Free add-on quotas.
- Whether generative AI works on Free.
- The behaviour of `so_` past a video's end.
- Search indexing delay.
- Escaping `|` and `=` in metadata.
- Cloudinary CORS headers for canvas use.

## Key sources
- Cloudinary:
  - Upload API reference: https://cloudinary.com/documentation/image_upload_api_reference
  - Unsigned upload parameters: https://cloudinary.com/documentation/ts_unsupported_parameters_in_unsigned_uploads
  - Upload Widget: https://cloudinary.com/documentation/upload_widget_reference
  - Folder modes: https://cloudinary.com/documentation/folder_modes
  - Layers: https://cloudinary.com/documentation/layers
  - Text layers: https://cloudinary.com/documentation/image_text_layers
  - Error codes: https://cloudinary.com/documentation/ts_what_are_the_common_error_codes_returned_in_the_x_cld_error_header_when_delivering_assets
  - Transformation counts: https://cloudinary.com/documentation/transformation_counts
  - Billing and plans: https://cloudinary.com/documentation/billing_and_plans
  - Admin API: https://cloudinary.com/documentation/admin_api
  - Search: https://cloudinary.com/documentation/search_method
  - Structured metadata: https://cloudinary.com/documentation/structured_metadata
  - Notifications: https://cloudinary.com/documentation/notifications
  - Add-ons: https://cloudinary.com/documentation/cloudinary_add_ons
  - AI Content Analysis: https://cloudinary.com/documentation/cloudinary_ai_content_analysis_addon
  - Geo-tagging blog: https://cloudinary.com/blog/geo-tag-your-images
- fastembed offline issue: https://github.com/qdrant/fastembed/issues/218
- CLIP models: https://huggingface.co/Qdrant/clip-ViT-B-32-vision
- pgvector: https://github.com/pgvector/pgvector · https://github.com/pgvector/pgvector-python
- Neon:
  - Connection pooling: https://neon.com/docs/connect/connection-pooling
  - Connection latency: https://neon.com/docs/connect/connection-latency
  - Free plan limits: https://neon.com/faqs/free-plan-limits-and-quotas
- Pillow:
  - Security: https://pillow.readthedocs.io/en/stable/handbook/security.html
  - GPS IFD: https://github.com/python-pillow/Pillow/issues/5863
  - pillow-heif: https://pillow-heif.readthedocs.io/en/latest/pillow-plugin.html
- CLIP paper: https://arxiv.org/pdf/2103.00020
- LLM:
  - LiteLLM Gemini: https://docs.litellm.ai/docs/providers/gemini
  - LiteLLM routing: https://docs.litellm.ai/docs/routing
  - Gemini rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
  - Gemini billing: https://ai.google.dev/gemini-api/docs/billing
- FastAPI CORS: https://fastapi.tiangolo.com/tutorial/cors/
- Frontend:
  - react-leaflet icons: https://github.com/PaulLeCam/react-leaflet/issues/808
  - OSM tile policy: https://operations.osmfoundation.org/policies/tiles/
- Deployment:
  - Render free: https://render.com/docs/free
  - Vite env: https://vite.dev/guide/env-and-mode
  - WSL networking: https://learn.microsoft.com/en-us/windows/wsl/networking
- Licensing:
  - NASA media: https://www.nasa.gov/nasa-brand-center/images-and-media/
  - Wikimedia reuse: https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia

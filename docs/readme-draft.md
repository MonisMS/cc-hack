# FieldProof

**FieldProof turns an NGO's field photos and videos into organised, searchable and traceable proof of impact.**

## The problem

NGOs and community groups collect photos and videos while planting trees, cleaning public spaces, repairing infrastructure and running other field projects. That evidence often stays scattered across phones and drives, making it hard to show what happened, where it happened and what changed. Building a donor-ready report means hours of manual sorting and choosing before-and-after images. Teams also need confidence that a published image and its numbers can be traced back to the original evidence.

## Features

| Feature | What it does |
|---|---|
| Bulk upload and automatic analysis | Upload photos and videos through Cloudinary, then extract dates and locations, create embeddings and add useful tags. |
| Projects, sites, map and timeline | Organise evidence by project, site and capture time so teams can see where and when work happened. |
| Activity and visual-signal tags | Identify things such as saplings, volunteers, floods, roads and solar panels for browsing and filtering. |
| Semantic and filtered search | Find relevant evidence with a plain-English query, even when the exact words are not in the asset's tags. |
| Before/after pairing and slider | Suggest photos from the same site, compare them side by side and show a visual change estimate. |
| Impact reports | Combine measured metrics, a grounded summary and photo evidence into a web report that can be printed to PDF. |
| Campaign kit | Create share-ready social crops, a quote card and a before/after collage using Cloudinary transformations. |
| Lineage and traceability | Show the source asset, transformations, output URL, model and time behind each report or campaign asset. |

## How we keep numbers honest

The AI is not allowed to invent numbers. It receives text with placeholders only; those placeholders are filled from measured data produced by the application. If grounded text cannot be generated, FieldProof uses a fixed template instead. This keeps report and comparison numbers tied to the underlying evidence.

## Privacy

Faces are blurred in images used for sharing. The API rounds GPS coordinates to three decimal places in public views. Uploads also require the uploader to tick a consent checkbox before the asset is registered.

## Honesty notes

- Green-cover percentage is an estimate based on image colour, not a scientific measurement.
- The demo before/after pair's date was adjusted because we only had one day available for the demonstration.

## Roadmap: not built yet

These ideas are outside the current submission build:

- Writing structured project, site and phase metadata back to Cloudinary.
- Automatic video transcription and chapters.
- Duplicate detection and a missing-EXIF integrity flag.
- A Cloudinary MCP server inside the report agent.
- Generative restore or cleanup effects.
- Multi-tenant organisations and a mobile app.
- Stronger authentication and offline-round polish.

## Team

| Person | Role |
|---|---|
| Monis | Owner; backend, demo data, deployment, merging PRs and submission |
| Ujjwal | Main frontend pages: library, asset, compare and report |
| Chaubey | Credits page, demo photos and README draft |
| Aditya | Search page, testing, screenshots and demo-video help |

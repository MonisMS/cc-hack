# Code Cubicle 6.0 — Problem Statements

**3 Oct Online · 11 Oct Offline**

---

## Problem Statement 01 — AI-Powered Data Intelligence Platform

Businesses often need to collect specific information from the web, such as job openings, sales leads, sponsor opportunities, market data, or other business-relevant information. However, building separate scrapers and workflows for every requirement is time-consuming, difficult to maintain, and not scalable.

The challenge is to build an AI-powered data intelligence platform where users can describe what they need in plain English. The AI should understand the request, dynamically create and execute an appropriate data-collection workflow, gather information from permitted sources, process and validate the data, and present the results through a centralized dashboard.

The platform should also allow users to manage collection tasks, monitor their progress, explore results, inspect sources, revisit previous workflows, and export datasets.

### Goal

Build a prompt-based AI Data Intelligence Platform that can:

- Understand data requirements from natural-language prompts.
- Dynamically design and execute data-collection workflows.
- Collect and process information from multiple permitted sources.
- Clean, structure, validate, and deduplicate results.
- Provide source-backed, traceable data.
- Allow users to monitor and manage collection tasks.
- Present results through an interactive dashboard.
- Maintain workflow and dataset history.
- Allow users to search, filter, and export collected data.

### Expected Outcome

A complete product that turns a natural-language business requirement into a clean, structured, source-backed dataset with a managed end-to-end workflow.

---

## Problem Statement 02 — AI-Powered Impact & Sustainability Media Platform (Cloudinary)

NGOs, governments, and sustainability organizations generate large volumes of photos and videos from field projects, environmental initiatives, infrastructure work, and community programs. Manually organizing, analyzing, verifying, and turning this media into meaningful evidence and reports is time-consuming and difficult to scale.

The challenge is to build an AI-powered media intelligence platform using Cloudinary that can understand field media, organize evidence by project, location, and timeline, and help teams turn visual data into reliable insights and impact stories.

### Goal

Build a complete platform that can:

- Analyze and intelligently organize large collections of image and video evidence.
- Identify relevant projects, activities, locations, and visual signals from media.
- Compare before-and-after media to demonstrate visible project or environmental changes.
- Generate visual reports, summaries, and campaign-ready content from collected evidence.
- Make media searchable through AI-powered metadata, tagging, and semantic discovery.
- Preserve traceability to the original source assets and transformations.

### Expected Outcome

A scalable media intelligence product that transforms raw field media into searchable evidence, measurable impact, and compelling visual stories.

---

## Problem Statement 03 — AI-Powered Edge Memory & Intelligence Platform

AI applications increasingly need to operate in environments where network connectivity is limited, latency is critical, and sensitive data cannot always leave the device. Robots, industrial systems, kiosks, vehicles, mobile devices, and other edge applications need to search and reason over locally generated information without continuously depending on a cloud service.

Building such systems is challenging because applications need to maintain local vector memory, perform fast semantic retrieval, work offline, handle continuously changing data, and synchronize relevant information with the cloud when connectivity becomes available.

The challenge is to build an AI-powered edge intelligence platform that uses Qdrant Edge to provide local semantic memory and retrieval, while intelligently managing the relationship between on-device data and centralized cloud knowledge.

### Goal

Build an offline-first AI application powered by Qdrant Edge that can:

- Maintain searchable semantic memory directly on an edge device.
- Perform low-latency vector and hybrid search without network access.
- Dynamically decide what information should remain local and what should be synchronized.
- Support intermittent connectivity and continue operating offline.
- Synchronize data between edge devices and Qdrant Server when connectivity returns.
- Handle evolving local memory, updates, and conflicting information.
- Provide a user-facing interface to inspect device memory, search results, synchronization status, and system activity.
- Demonstrate a meaningful edge-to-cloud AI workflow, rather than simply running a local vector database.

### Expected Outcome

A complete edge-native AI product that can remember, retrieve, operate offline, and synchronize intelligently when connected.

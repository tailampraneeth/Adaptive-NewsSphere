# Heimdall — Platform Limitations & Scaling Guide

This document provides a transparent overview of the architectural constraints and rate limits imposed by the free-tier cloud resources used to host Heimdall. It serves as an operational guide for developers looking to scale the platform.

---

## 1. Cloud Infrastructure Constraints (Free Tier)

### Neon Serverless PostgreSQL
- **Storage Cap:** **0.5 GB** of data.
- **Compute Auto-suspend:** Databases auto-suspend after 5 minutes of inactivity. The first request after suspension experiences a cold start delay of **2–5 seconds**.
- **Index Cost:** Indexing columns increases storage consumption. PostgreSQL Full-Text Search GIN indexes require approximately **15-20%** of the size of the text columns being indexed.

### Render Web Services (Backend API)
- **CPU & Memory:** **512 MB RAM** and shared CPU.
- **Cold Start:** Inactive web services spin down. A request to a spun-down service experiences a cold start boot delay of **30–50 seconds**.
- **No Background Persistent Storage:** Disk space on Render is ephemeral. All uploads or persistent logs must live in PostgreSQL.

### Vercel (Frontend SPA)
- **Serverless Execution:** Serverless functions are not used for rendering (SPA only). All API calls proxy directly to Render.
- **Bandwidth:** **100 GB** monthly transfer limit.

---

## 2. API Quotas & Ingestion Limits

### Google Gemini API (Free Tier)
- **Rate Limit:** **15 Requests Per Minute (RPM)**.
- **Daily Quota:** **1,000,000 tokens per day**.
- **Ingestion Quota Guard:**
  - Standard RSS ingestion happens every 30 minutes, adding ~30 stories.
  - Summarization happens 10 minutes later. The batch size is capped at **30 stories per run** (`LIMIT 30` in `/internal/summarize`) to prevent exceeding Gemini's 15 RPM limit and keeping daily usage around **720,000 tokens**.

---

## 3. Engineering Constraints & Anti-Patterns

- **No Redis Session Cache:** Auth relies exclusively on stateless JWT tokens. Token expiration is hardcoded to **7 days** (configurable via env). If token revocation or session blacklisting is required, the database must be queried, which impacts read latency.
- **Single Backend Threading:** FastAPI runs on a single node on Render. High concurrent traffic (> 200 DAU simultaneously) will experience queueing delays.
- **No Collaborative Filtering:** Personalization calculations are strictly deterministic and run in-memory per-request. There is no background worker calculating recommendation matrices.

# Heimdall — World News Intelligence Watchtower

> *See the World's Stories Before They Reach Everyone Else.*

Heimdall is a lightweight, high-performance, PWA-compliant news intelligence platform. It ingests streams of articles from RSS feeds, groups them into coherent story clusters, runs deterministic verification checks, and delivers a ranked, personalized feed to users.

Heimdall is built specifically to run completely on **free-tier services** (Neon DB, Render backend, Vercel frontend, Gemini API), dropping heavyweight requirements like Redis or Qdrant vector databases in favor of optimized PostgreSQL indexing.

---

## Technical Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI (Python 3.13) |
| Relational DB | PostgreSQL 16 (Neon / Local port **5433**) with GIN indexes |
| Dev/Test DB | SQLite `:memory:` (auto-fallback offline) |
| Front-end | React 19 + Vite + Vanilla CSS |
| PWA Compliance | Service Worker caching (last 20 stories offline) + Manifest |
| AI Summary | Google Gemini API (free tier) with fallback |
| NLP & Clustering | spaCy + Jaccard token overlap (CPU friendly) |

---

## Key Features

1. **Deterministic Clustering:** Jaccard title token overlap ($\ge 0.40$) and keyword overlap within 12-hour windows groups articles without expensive vectors.
2. **Consensus Verification:** Computes contradiction matrices, publisher diversity, and source agreement levels using Jaccard token matches.
3. **PostgreSQL FTS Search:** Direct full-text search utilizing `ts_rank` over a `search_vector` column synchronized via triggers, with fallback to SQLite `LIKE` in development.
4. **Scored SQL Recommendation:** Sorts stories dynamically using interests match, publisher affinities, and region boosts.
5. **Reading Completion Feedback:** Automatically monitors scroll depth and dwell time. Reaching $\ge 70\%$ depth boosts the category score ($+0.10$), while leaving $\le 20\%$ applies an abandonment penalty ($-0.10$).
6. **Norse-Themed UI:** Sleek, modern dark-space default layout (dark/light toggles) matching premium design aesthetics.
7. **Daily Briefing:** Displays a customized top 5 briefings banner corresponding to morning/afternoon/evening preference slots.
8. **Secure Password Recovery:** Integrated forgot-password and reset-password flows with cryptographic token hashing, rate-limiting, anti-user enumeration, and SMTP dispatch with fallback console logging.

---

## Local Development Setup

### 1. Backend Setup
1. Copy environmental template:
   ```bash
   cp .env.example .env
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
4. Run Alembic schema migrations:
   ```bash
   alembic upgrade head
   ```
5. Seed publishers and test accounts:
   ```bash
   python scripts/seed_publishers.py
   python scripts/seed_users.py
   ```
6. Launch API server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 2. Frontend Setup
1. Go to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```
2. Launch Vite dev server:
   ```bash
   npm run dev
   ```
3. Open the web interface at `http://localhost:5173`.

### 3. Run Verification Tests
To execute the automated backend validation suite:
```bash
cd backend
python -m pytest tests/
```
All tests are configured to automatically fall back to an in-memory SQLite database when PostgreSQL is offline, ensuring zero external environment requirements.

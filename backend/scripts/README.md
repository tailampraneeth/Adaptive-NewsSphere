# Adaptive NewsSphere — Backend Scripts Reference

All scripts are run from the `e:\News\backend\` directory with the virtualenv activated.

```powershell
cd e:\News\backend
..\.venv\Scripts\activate
```

---

## 🏗️ Infrastructure

| Script | Purpose |
|--------|---------|
| `scripts\start-dev.ps1` | Start full Docker dev stack (Postgres, Redis, Qdrant) + Uvicorn |
| `scripts\stop-dev.ps1` | Stop Docker dev stack |
| `scripts\verify_infra.py` | Verify Postgres, Redis, Qdrant are all reachable |
| `scripts\verify_backend.py` | Verify full backend stack (DB schema + API health) |
| `scripts\reset_db.py` | **⚠️ DESTRUCTIVE** Drop and recreate all database tables |

---

## 📰 Data Collection Pipeline

Run these in order on first setup (or when refreshing the dataset):

### Step 1 — Collect news articles
```powershell
python scripts\collect_news.py
```
Fetches RSS feeds from all configured publishers, deduplicates, and saves raw articles to Postgres. Target: 500–1000 articles across 12+ publishers.

### Step 2 — NLP enrichment
```powershell
python scripts\enrich_articles.py
```
Runs spaCy NER, KeyBERT keyword extraction, and frequency-based topic extraction on all unenriched articles. Writes `keywords`, `named_entities`, `topics`, `word_count`, `reading_time` to the database.

### Step 3 — Semantic clustering
```powershell
python scripts\run_clustering.py
```
Groups related articles into Stories using `all-MiniLM-L6-v2` embeddings and cosine similarity (threshold 0.82). Assigns story titles, importance scores, trending scores, and formation evidence.

### Step 4 — Category classification
```powershell
# First run (classify all NULL articles)
python scripts\classify_categories.py

# Force re-classify everything
python scripts\classify_categories.py --force
```
Assigns `predicted_category` and `category_confidence` to every article using embedding similarity against 10 category anchors, with keyword fallback.

---

## 📊 Analytics & Quality

| Script | Usage | Purpose |
|--------|-------|---------|
| `scripts\generate_analytics.py` | `python scripts\generate_analytics.py` | Generate dataset analytics report (article count, category dist, publisher stats) |
| `scripts\validate_dataset.py` | `python scripts\validate_dataset.py` | Validate data quality (null checks, hash integrity, NLP completeness) |
| `scripts\update_feed_health.py` | `python scripts\update_feed_health.py` | Update publisher feed health metrics (latency, success rate, duplicate %) |

---

## 🔄 Maintenance

| Script | Usage | Purpose |
|--------|-------|---------|
| `scripts\refresh_scores.py` | `python scripts\refresh_scores.py` | Recalculate story importance/trending scores (run every 4–6 hours) |
| `scripts\refresh_scores.py` | `python scripts\refresh_scores.py --batch-size 50` | Run with smaller batches to reduce memory usage |

### Recommended refresh schedule

Add to Task Scheduler or PowerShell scheduled job:
```powershell
# Run every 6 hours
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 6) -Once -At (Get-Date)
$action  = New-ScheduledTaskAction -Execute "python" -Argument "scripts\refresh_scores.py" -WorkingDirectory "e:\News\backend"
Register-ScheduledTask -TaskName "NewsSphere-ScoreRefresh" -Trigger $trigger -Action $action
```

---

## 🧪 Testing

```powershell
# Run all tests
..\.venv\Scripts\python -m pytest tests\ -v

# Run with coverage report
..\.venv\Scripts\python -m pytest tests\ --cov=app --cov-report=term-missing

# Run specific test file
..\.venv\Scripts\python -m pytest tests\test_clustering.py -v
```

> **Prerequisites:** Postgres (port 5433), Qdrant (port 6333) must be running. Start with `.\scripts\start-dev.ps1`.

---

## 🔍 Linting & Type Checking

```powershell
# Ruff linting (auto-fix)
..\.venv\Scripts\python -m ruff check app\ --fix

# Type checking
..\.venv\Scripts\python -m mypy app\ --ignore-missing-imports
```

---

## Environment Variables

All configuration is driven by the `.env` file in `e:\News\`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5433` | Host-mapped port (5433 to avoid conflict with native PG) |
| `POSTGRES_DB` | `newssphere` | Database name |
| `POSTGRES_USER` | `developer` | Database user |
| `POSTGRES_PASSWORD` | `LocalPassword123` | Database password |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector DB URL |
| `STORY_SIMILARITY_THRESHOLD` | `0.82` | Cosine similarity threshold for story clustering |

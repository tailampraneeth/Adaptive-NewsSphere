# Adaptive NewsSphere (ANS) Backend

Adaptive NewsSphere is an AI-powered, personalized news intelligence platform. This repository contains the core Python backend, database mappings, semantic clustering engine, and automatic category classification pipeline structured using Clean Architecture principles.

---

## 1. Project Overview & Features

Adaptive NewsSphere acts as an autonomous aggregator and analyzer of global news, extracting raw articles from various RSS feeds, parsing and cleaning content, computing embeddings, detecting duplicate coverage, and dynamically organizing articles into cohesive "Stories".

### Key Features (Milestone 2: Semantic Intelligence Foundation)
*   **Automatic Category Classification (Multi-Tier):** Classifies articles into 10 target categories using (a) RSS tags, (b) Qdrant nearest-neighbor categorized article labels ($\ge 0.80$ similarity), (c) embedding similarity against pre-computed centroids ($\ge 0.45$), or (d) keyword frequency heuristics.
*   **Semantic Story Clustering:** Leverages `Sentence-Transformers` (`all-MiniLM-L6-v2`) and Qdrant vector database to group related articles into unified Story clusters.
*   **Explainable Story Formation (XAI):** Automatically extracts and stores named entities (persons, organizations, locations), shared keywords, topics, publisher diversity, and average cluster similarity.
*   **Multi-Class Duplicate Taxonomy & Quality Penalty:** Automatically tags duplicates as `EXACT_DUPLICATE`, `SEMANTIC_DUPLICATE`, `UPDATED_ARTICLE`, or `CORRECTED_ARTICLE`. Applies a 50% quality score penalty on exact and semantic duplicates to prevent cluster pollution.
*   **Centroid-Representative Metadata:** Computes centroid-nearest representative article IDs and builds a structured RAG (Retrieval-Augmented Generation) context JSON block for every story.
*   **Feed Health & Latency Monitoring:** Tracks response latencies, success/failure counts, duplicate percentages, and articles-per-crawl inline during crawler executions.
*   **Observability Metrics:** Measures execution times across all processing phases (fetch, clean, embed, index, cluster) and exposes them via a dedicated `/api/v1/metrics` endpoint.

---

## 2. Technology Stack

*   **API Framework:** FastAPI (Asynchronous Web Framework)
*   **Relational Database:** PostgreSQL 16 (running on port **5433** to avoid native host conflicts)
*   **Cache & Feature Store:** Redis (running on port **6379**)
*   **Vector Search Database:** Qdrant (running on port **6333**)
*   **ORM Mapping:** SQLAlchemy 2.0 (using `asyncpg` async driver)
*   **Database Migrations:** Alembic
*   **Semantic Embeddings:** HuggingFace `sentence-transformers` (`all-MiniLM-L6-v2` - 384 dimensions)
*   **NLP & Metadata Extraction:** Spacy & BeautifulSoup4

---

## 3. Architecture & Folder Structure

The project follows a modular, clean monolith design:

```text
backend/
├── app/
│   ├── api/                # Routing, controllers, and metrics endpoint layers
│   ├── core/               # Configuration (config.py) and logging (logging.py)
│   ├── database/           # Connection handlers and ORM models
│   │   ├── connection.py   # Async database session manager
│   │   ├── migrations/     # Alembic schema migrations and history
│   │   └── models/         # Segmented domain schemas (Article, Story, Duplicate, etc.)
│   ├── services/           # Business logic (Ingestion, Clustering, Classification)
│   ├── utils/              # Cleaners and hash helpers
│   └── workers/            # Ingest standalone runners
└── tests/                  # Pytest verification suites (100% async coverage)
```

---

## 4. Local Development & Installation Guide

### Prerequisites
*   Windows 11 with **WSL2** enabled.
*   **Python 3.13** installed on host.
*   **Docker Desktop** installed and running.

### 1. Copy Local Configuration
From the workspace root directory, copy the environment template:
```bash
cp .env.example .env
```

### 2. Infrastructure Setup (Docker Compose)
We provide a Windows PowerShell script to automate checks, verify port states, spin up containers, and run migrations in a single command:
```powershell
.\backend\scripts\start-dev.ps1
```
*Alternatively, to start manually:*
```bash
docker compose up -d
cd backend
alembic upgrade head
```

### 3. Running the Data Pipeline
Execute the data processing steps sequentially to crawl feeds, enrich content, cluster stories, and classify categories:
```powershell
# 1. Fetch RSS feeds (Ingestion)
$env:PYTHONPATH="backend"
python backend/scripts/collect_news.py

# 2. Enrich content with NLP
python backend/scripts/enrich_articles.py

# 3. Group articles into Stories
python backend/scripts/run_clustering.py

# 4. Classify categories on all articles
python backend/scripts/classify_categories.py --force

# 5. Compile dataset quality & metrics report
python backend/scripts/generate_analytics.py
```

### 4. Running unit and integration tests
Ensure all unit and integration tests pass cleanly:
```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests/ -v
```

### 5. Launch FastAPI Application Server
Start the development server:
```bash
cd backend
uvicorn app.main:app --reload
```
*   **Interactive Swagger API Docs:** http://localhost:8000/docs
*   **Database Connection Health Endpoint:** http://localhost:8000/health
*   **Application Observability Metrics:** http://localhost:8000/api/v1/metrics

### 6. Tear Down Infrastructure
To stop all Docker containers and clean up the virtual network:
```powershell
.\backend\scripts\stop-dev.ps1
```

---

## 5. Environment Variables

The application reads configurations from the `.env` file at root:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LOG_LEVEL` | Level of logging output (e.g., `INFO`, `DEBUG`) | `INFO` |
| `POSTGRES_PORT` | Port of the local Postgres container | `5433` |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Connection URL for local Redis cache | `redis://localhost:6379/0` |
| `QDRANT_URL` | Connection URL for local Qdrant server | `http://localhost:6333` |
| `GEMINI_API_KEY` | Google AI Studio key (optional placeholder) | `your_gemini_api_key_here` |

---

## 6. Project Roadmap

*   **[x] Milestone 1: Data Pipeline Foundations** (RSS Parser, Postgres, Redis caching, migrations, docker setups).
*   **[x] Milestone 2: Semantic Intelligence Foundation** (Clustering, Category classification fallbacks, RAG Context, Duplicate taxonomies, Metrics APIs).
*   **[ ] Milestone 3: Real-Time Personalization & Verification** (User personalization, credibility scoring, LLM fact-checking).
*   **[ ] Milestone 4: Web UI & Dashboard** (Interactive user interface).

---

## 7. Screenshots Placeholder

*(UI Dashboard and story visualization screenshots will be added here upon completion of Milestone 4)*

---

## 8. License & Contributing

### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Contributing
Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on submitting pull requests.

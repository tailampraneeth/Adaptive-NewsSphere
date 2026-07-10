# Adaptive NewsSphere — AI-Powered News Intelligence Platform

Adaptive NewsSphere is a fully deterministic, AI-powered personalized news intelligence platform. The backend implements semantic clustering, story verification, and a recommendation engine — all without LLMs, paid APIs, or cloud services.

**Current Release:** `v0.5.0` — Conversational AI

---

## Milestone Progress

| Milestone | Name | Status |
|---|---|---|
| 1 | Infrastructure & Ingestion | ✅ Released (v0.1.0) |
| 2 | Semantic Intelligence | ✅ Released (v0.2.0) |
| 3 | Story Intelligence & Verification | ✅ Released (v0.3.0) |
| 4 | Recommendation Engine | ✅ Released (v0.4.0) |
| **5** | **Conversational AI (Q&A)** | **✅ Released (v0.5.0)** |
| 6 | Frontend & Auth | 🔜 Planned |

---

## Technical Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI (async) |
| Relational DB | PostgreSQL 16 (Docker, port **5433**) |
| Vector DB | Qdrant (Docker, port **6333**) |
| Cache | Redis (Docker, port **6379**) |
| ORM | SQLAlchemy 2.0 (asyncpg) |
| Migrations | Alembic |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`, 384-dim, CPU) |
| NLP | spaCy + KeyBERT (deterministic, no LLMs) |

---

## API Endpoints (v5.0.0)

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Welcome + version info |
| `GET` | `/health` | Database connectivity check |
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/api/v1/metrics` | Pipeline performance statistics |
| `POST` | `/api/v1/metrics/reset` | Reset metrics (dev only) |
| `GET` | `/api/v1/feed/health` | Global recommendation engine health |
| `GET` | `/api/v1/feed/{user_id}` | Personalized ranked news feed |
| `POST` | `/api/v1/feed/interact` | Record user interaction |
| `GET` | `/api/v1/feed/{user_id}/profile/health` | User profile diagnostics |
| `POST` | `/api/v1/chat/sessions` | Create conversational RAG session |
| `GET` | `/api/v1/chat/sessions/{session_id}` | Get session details & history |
| `POST` | `/api/v1/chat/sessions/{session_id}/message` | Send message (streaming/sync) |
| `GET` | `/api/v1/chat/sessions/user/{user_id}/list` | List user sessions |
| `DELETE` | `/api/v1/chat/sessions/{session_id}` | Delete conversational session |
| `GET` | `/api/v1/chat/health` | Chat RAG pipeline diagnostics |

---

## Port Conflict Design (Why Port 5433?)

PostgreSQL maps to host port **5433** (`5433:5432`) to prevent conflicts with any native PostgreSQL service on port 5432. To revert to 5432, update `docker-compose.yml` and `.env`.

---

## Local Development Setup

### 1. Prerequisites
- Windows 11 with **WSL2** enabled
- **Python 3.13** installed on host
- **Docker Desktop** installed and running

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Start Infrastructure
```powershell
.\backend\scripts\start-dev.ps1
```
Or manually:
```bash
docker compose up -d
cd backend && alembic upgrade head
```

### 4. Run Tests
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest backend/tests/ -v
```
Expected: **81 tests passed**

### 5. Launch API Server
```bash
cd backend
uvicorn app.main:app --reload
```
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Feed: http://localhost:8000/api/v1/feed/{user_id}

### 6. Seed Test Users
```bash
$env:PYTHONPATH="backend"
python backend/scripts/seed_users.py
```

### 7. Run Analytics Report
```bash
$env:PYTHONPATH="backend"
python backend/scripts/generate_analytics.py
```

### 8. Stop Infrastructure
```powershell
.\backend\scripts\stop-dev.ps1
```

---

## Codebase Directory Layout

```text
backend/
├── app/
│   ├── api/routes/         # Routing: metrics.py, feed.py
│   ├── core/               # config.py (all settings & feature flags), logging.py
│   ├── database/
│   │   ├── connection.py   # Async session manager
│   │   ├── migrations/     # Alembic schema versions
│   │   └── models/         # Domain models: user, user_profile, article, story,
│   │                       #   recommendation, interaction, conversation, ...
│   ├── services/           # Business logic: clustering, nlp_processor,
│   │                       #   preference_engine, feed_assembler, vector_store
│   ├── utils/              # Text cleaners, hash helpers
│   └── workers/            # rss_worker, preference_worker
├── scripts/
│   ├── generate_analytics.py  # 13-section analytics report
│   ├── seed_users.py          # Dev utility: seed test users
│   └── ...
└── tests/                  # pytest suites (81 tests)

docs/
├── recommendation-engine.md   # Recommendation engine design docs
├── conversational-rag.md      # Conversational RAG pipeline reference
└── conversation-engine.md     # RAG Refined telemetry architecture design
```

---

## Engineering Philosophy

- 🚫 **No LLMs** — all intelligence is deterministic (EMA, cosine similarity, exponential decay)
- 🆓 **Completely free** — no paid APIs, no cloud services
- 🏠 **Local-first** — Redis + Qdrant + PostgreSQL in Docker
- 🤖 **CPU-friendly** — all inference uses lightweight sentence-transformers
- ⚙️ **Configurable** — all ranking weights and feature flags in `config.py`
- 🧩 **Modular Monolith** — Clean Architecture, independently testable services

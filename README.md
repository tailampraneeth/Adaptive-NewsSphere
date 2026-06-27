# Adaptive NewsSphere Backend (Milestone 1)

Adaptive NewsSphere is an AI-powered personalized news intelligence platform. This repository contains the core Python backend, database mappings, and ingestion pipelines structured using Clean Architecture principles.

---

## Technical Stack
*   **API Framework:** FastAPI (Asynchronous Web Framework)
*   **Relational Database:** PostgreSQL 16 (running in Docker container on port **5433**)
*   **Cache & Feature Store:** Redis (running in Docker container on port **6379**)
*   **Vector Search Engine:** Qdrant (running in Docker container on port **6333**)
*   **ORM Mapping:** SQLAlchemy 2.0 (using `asyncpg` async driver)
*   **Database Migrations:** Alembic

---

## Port Conflict Design (Why Port 5433?)
To ensure a frictionless local development experience, this project maps the PostgreSQL container to host port **5433** (`5433:5432`). 
*   This prevents conflicts with any native PostgreSQL Windows service that might already be running on port **5432**.
*   The container still listens on port **5432** internally, meaning no modifications are needed inside the Docker virtual network.
*   *Note:* If you do not have PostgreSQL installed natively on your host machine and wish to restore the default port mapping to `5432`, simply update `ports` in `docker-compose.yml` to `"5432:5432"` and modify `POSTGRES_PORT=5432` inside your `.env` file.

---

## Local Development Setup

### 1. Prerequisites
*   Windows 11 with **WSL2** enabled.
*   **Python 3.13** installed on host.
*   **Docker Desktop** installed and running.

### 2. Copy Local Configuration
From the workspace root directory `E:\News`, copy the configuration template:
```bash
cp .env.example .env
```

### 3. Spin Up Infrastructure
We provide a Windows PowerShell script to automate checks, verify port states, spin up containers, and run migrations in a single command:
```powershell
.\backend\scripts\start-dev.ps1
```
*Alternatively, to do it manually:*
```bash
# 1. Start containers in daemon mode
docker compose up -d

# 2. Apply database migrations
cd backend
alembic upgrade head
```

### 4. Run Pytest Suites
Ensure all unit and integration tests pass:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest backend/tests/
```

### 5. Launch FastAPI Application Server
Start the FastAPI development server with hot reload enabled:
```bash
cd backend
uvicorn app.main:app --reload
```
*   **Interactive API Docs:** http://localhost:8000/docs
*   **Database Connection Health Endpoint:** http://localhost:8000/health

### 6. Tear Down Infrastructure
To stop all Docker containers and clean up the virtual network:
```powershell
.\backend\scripts\stop-dev.ps1
```
*(Or manually run `docker compose down`)*

---

## Codebase Directory Layout

```text
backend/
├── app/
│   ├── api/                # Routing, controllers, and endpoint layers
│   ├── core/               # App configuration (config.py) and logging (logging.py)
│   ├── database/           # Connection handlers and ORM models
│   │   ├── connection.py   # Async database session manager
│   │   ├── migrations/     # Alembic schema migrationsversions
│   │   └── models/         # Segmented domain schemas (user, article, story, etc.)
│   ├── services/           # Business logic (RSS ingestion parsing)
│   ├── utils/              # Cleaners and hash helpers
│   └── workers/            # Ingest standalone runners
└── tests/                  # Pytest verification suites
```

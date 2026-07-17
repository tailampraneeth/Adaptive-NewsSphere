# Heimdall Migration Guide: Enterprise to Consumer Edition

This guide explains how to migrate an existing **Adaptive NewsSphere** (Enterprise Edition) installation to the lightweight **Heimdall** (Consumer Edition) architecture.

---

## 1. Dependency Cleanup
The consumer edition prunes heavyweight, CPU-demanding machine learning libraries to fit into free-tier cloud containers:

1. Open your terminal in the backend workspace.
2. Uninstall legacy machine learning dependencies:
   ```bash
   pip uninstall torch sentence-transformers transformers keybert qdrant-client redis
   ```
3. Install the updated requirements:
   ```bash
   pip install -r backend/requirements.txt
   ```

---

## 2. Infrastructure Decommissioning
1. **Redis Cache:** Decommission the Redis cluster.
2. **Qdrant Vector Database:** Delete or spin down the Qdrant instance. Vector embeddings and similarity indexing are no longer required; semantic clustering is replaced by lightweight Jaccard title token matching.

---

## 3. Database Schema Migration
To migrate your PostgreSQL database from the enterprise schema to the refined Heimdall schema:

1. Stop any running ingestion schedulers or workers.
2. Set the environment variable `DATABASE_URL` pointing to your target database.
3. Apply the Alembic migration script to drop old enterprise tables (`user_profiles`, `user_interactions`, `chat_sessions`, `chat_messages`, `article_duplicates`) and establish the new Heimdall tables (`bookmarks`, `reading_history`):
   ```bash
   cd backend
   alembic upgrade head
   ```

---

## 4. Ingestion Webhook Setup
1. Schedule a webhook caller (e.g. GitHub Actions or standard cron) to POST to `/api/v1/internal/ingest` and `/api/v1/internal/summarize` at regular intervals.
2. Pass the `X-Ingest-Secret` header to authorize ingestion webhooks.

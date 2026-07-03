# Adaptive NewsSphere — System Architecture

> **Milestone 2 — Semantic Intelligence Foundation**
> Status: Production-ready local development environment

---

## Overview

Adaptive NewsSphere is a fully local, open-source AI-powered news aggregation and personalisation platform. The backend is designed as a **resume-quality portfolio project** that demonstrates:

- RSS ingestion with deduplication
- NLP enrichment (NER, keyword extraction, topic detection)
- Semantic article clustering into Stories via vector similarity
- Automatic category classification
- Story quality scoring (importance, trending)
- Explainable AI evidence for story formation
- Vector search via Qdrant

Everything runs locally on a single developer machine with `docker compose up -d`.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API Framework | FastAPI 0.111 | Async HTTP API |
| ORM | SQLAlchemy 2.0 (asyncpg) | Postgres models and migrations |
| Migrations | Alembic | Schema versioning |
| Relational DB | PostgreSQL 16 (Docker) | Persistent article/story storage |
| Vector DB | Qdrant (Docker) | Semantic search and centroid storage |
| Cache | Redis (Docker) | (Reserved for Milestone 3+ session/rate cache) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers) | 384-dim semantic vectors |
| NLP | spaCy `en_core_web_sm` + KeyBERT | NER + keyword extraction |
| Containerisation | Docker Compose | One-command reproducible environment |

---

## High-Level Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                         │
│                                                                   │
│  RSS Feeds → IngestionService → Article (Postgres)               │
│               (feedparser + html_cleaner + SHA-256 dedup)        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ (raw articles, no NLP yet)
┌──────────────────────────────▼──────────────────────────────────┐
│                    NLP ENRICHMENT LAYER                          │
│                                                                   │
│  NLPProcessorService:                                             │
│    - spaCy en_core_web_sm → NER (PERSON, ORG, GPE)              │
│    - KeyBERT (shared SentenceTransformer) → top-5 keywords       │
│    - Noun chunk frequency → top-3 topics                         │
│                                                                   │
│  CategoryClassifierService:                                       │
│    - Tier 1: Cosine similarity vs 10 category anchor embeddings  │
│    - Tier 2: Keyword frequency fallback (if confidence < 0.45)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ (enriched articles with NLP metadata)
┌──────────────────────────────▼──────────────────────────────────┐
│                 SEMANTIC CLUSTERING LAYER                         │
│                                                                   │
│  EmbedderService:                                                 │
│    - all-MiniLM-L6-v2 → 384-dim vectors                         │
│    - Input: f"{title}. {body[:1000]}"                            │
│                                                                   │
│  VectorStoreService (Qdrant):                                     │
│    - "articles" collection: per-article embedding (COSINE)       │
│    - "stories"  collection: per-story centroid (running average) │
│                                                                   │
│  ClusteringService:                                               │
│    1. content_hash exact dup check                               │
│    2. Embed article → upsert to "articles"                       │
│    3. search_similar("articles", top_k=5)                        │
│    4. If best_score > 0.82 → merge into existing Story          │
│       Else → create new Story                                    │
│    5. Update centroid in "stories"                               │
│    6. Update: title, importance_score, trending_score,           │
│               formation_evidence, first_reported_at, last_updated│
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      PERSISTENCE LAYER                           │
│                                                                   │
│  PostgreSQL (Docker, port 5433):                                  │
│    stories, articles, publishers, users,                         │
│    story_relations, story_timelines,                             │
│    article_duplicates, chat_sessions, chat_messages,             │
│    user_interactions, user_recommendation_logs                   │
│                                                                   │
│  Qdrant (Docker, port 6333):                                      │
│    "articles" — article embeddings (384-dim COSINE)              │
│    "stories"  — story centroid embeddings (384-dim COSINE)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Story Lifecycle

```
                     [Article Ingested]
                            │
              ┌─────────────▼──────────────┐
              │  content_hash duplicate?   │
              └─────────────┬──────────────┘
                   YES      │       NO
              ┌─────────────┘  ┌───────────┐
              ▼                ▼           │
    Link to existing     Embed article     │
    story as              ↓                │
    EXACT_DUPLICATE   Search Qdrant        │
                       top-5 similar       │
                            │              │
              ┌─────────────▼──────────────┐
              │  cosine > 0.82?            │
              └─────────────┬──────────────┘
                   YES      │       NO
                   ▼        │       ▼
            Merge into      │    Create new
            existing Story  │    Story (seed)
                   │        │       │
                   └────────┴───────┘
                            │
              ┌─────────────▼──────────────┐
              │  Update Story Quality      │
              │  - title (centroid-nearest)│
              │  - importance_score        │
              │  - trending_score          │
              │  - formation_evidence      │
              │  - first/last_reported_at  │
              └────────────────────────────┘
```

---

## Story Quality Signals

| Signal | Formula | Use Case |
|--------|---------|---------|
| `importance_score` | `0.35×count + 0.35×publisher_div + 0.20×freshness(24h) + 0.10×confidence` | General recommendation ranking |
| `trending_score` | `0.40×recency(6h) + 0.30×growth_rate + 0.30×publisher_div` | Home feed trending section |
| `confidence_score` | Mean embedding similarity of member articles to centroid | Data quality indicator |

---

## Duplicate Classification

| Type | Trigger | Action |
|------|---------|--------|
| `EXACT_DUPLICATE` | Same `content_hash` | Link to original story, record in `article_duplicates` |
| `SEMANTIC_DUPLICATE` | cosine similarity ≥ 0.95 | Link to same story, record in `article_duplicates` |
| `UPDATED_ARTICLE` | (reserved Milestone 3) | — |
| `CORRECTED_ARTICLE` | (reserved Milestone 3) | — |

---

## Database Schema Overview

```
publishers ─── articles ─── stories ─── story_relations (self-ref)
                   │             │
                   │        story_timelines
                   │        chat_sessions ─── chat_messages
                   │
              article_duplicates (provenance)
              user_interactions
              user_recommendation_logs

users ─── user_interactions
      ─── chat_sessions
      ─── user_recommendation_logs
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Welcome + version info |
| `GET` | `/health` | Postgres connectivity check |
| `GET` | `/api/v1/metrics` | Pipeline performance statistics |
| `POST` | `/api/v1/metrics/reset` | Reset metrics (dev only) |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Reserved for Milestone 3

The following fields exist in the schema but contain no business logic yet:

| Model | Field | Purpose |
|-------|-------|---------|
| `Story` | `verification_score` | Fact-check aggregate score |
| `Story` | `credibility_score` | Weighted publisher credibility |
| `Story` | `summary_quick` | AI-generated quick summary |
| `Story` | `summary_beginner` | AI-generated beginner summary |
| `Story` | `summary_professional` | AI-generated expert summary |
| `Article` | `UPDATED_ARTICLE` type | RSS update detection |
| `Article` | `CORRECTED_ARTICLE` type | Correction detection |

---

## One-Command Startup

```bash
docker compose up -d
```

Then run the data pipeline:
```powershell
python scripts\collect_news.py
python scripts\enrich_articles.py
python scripts\run_clustering.py
python scripts\classify_categories.py
```

See `scripts\README.md` for the full reference.

# Adaptive NewsSphere — System Architecture

> **Current Release: v0.4.0 — Recommendation Engine**
> Status: 4 of 6 milestones complete. Local-first. Docker-based. No LLMs. No paid APIs.

---

## Overview

Adaptive NewsSphere is a fully local, open-source, AI-powered news aggregation and personalisation platform. The backend is a **resume-quality portfolio project** built as a Modular Monolith following Clean Architecture principles.

The system ingests articles from RSS feeds, enriches them with NLP metadata, clusters semantically related articles into evolving Stories, verifies their factual integrity, and delivers a ranked, personalized feed to each user — entirely deterministically, without any LLMs or paid APIs.

Everything runs locally on a single developer machine with `docker compose up -d`.

---

## Milestone Progress

| # | Milestone | Status | Release |
|---|-----------|--------|---------|
| 1 | Infrastructure & Ingestion | ✅ Complete | v0.1.0 |
| 2 | Semantic Intelligence | ✅ Complete | v0.2.0 |
| 3 | Story Intelligence & Verification | ✅ Complete | v0.3.0 |
| 4 | Recommendation Engine | ✅ Complete | v0.4.0 |
| 5 | Conversational AI (Q&A) | 🔜 Planned | v0.5.0 |
| 6 | Frontend & Auth | 🔜 Planned | v0.6.0 |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API Framework | FastAPI (async) | HTTP API + background tasks |
| ORM | SQLAlchemy 2.0 (asyncpg) | Async Postgres models |
| Migrations | Alembic | Schema versioning |
| Relational DB | PostgreSQL 16 (Docker, port **5433**) | All persistent relational data |
| Vector DB | Qdrant (Docker, port **6333**) | Semantic search + preference vectors |
| Cache | Redis (Docker, port **6379**) | Preference ID hot cache (TTL 7 days) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers) | 384-dim CPU-friendly semantic vectors |
| NLP | spaCy `en_core_web_sm` + KeyBERT | NER + keyword extraction |
| Containerisation | Docker Compose | One-command reproducible environment |

---

## High-Level System Map

```
┌──────────────────────────────────────────────────────────────────┐
│                     MILESTONE 1: INGESTION                        │
│                                                                    │
│  RSS Feeds → IngestionService → Article (Postgres)                │
│              feedparser + html_cleaner + SHA-256 dedup            │
│              Publisher registry (credibility_score, bias_rating)  │
└───────────────────────────────┬──────────────────────────────────┘
                                │ raw articles
┌───────────────────────────────▼──────────────────────────────────┐
│                  MILESTONE 2: SEMANTIC INTELLIGENCE               │
│                                                                    │
│  NLPProcessorService:                                              │
│    - spaCy → NER (PERSON, ORG, GPE)                              │
│    - KeyBERT (shared SentenceTransformer) → top-5 keywords        │
│    - Noun chunk frequency → top-3 topics                          │
│                                                                    │
│  CategoryClassifierService:                                        │
│    - Tier 1: Cosine similarity vs 10 category anchor embeddings   │
│    - Tier 2: Keyword frequency fallback (if confidence < 0.45)    │
│                                                                    │
│  ClusteringService (Qdrant ANN):                                   │
│    - Embed article → upsert to "articles" collection              │
│    - Search "stories" centroids: cosine > 0.82 → merge           │
│    - Else → new Story (seed centroid)                             │
│    - Update: importance_score, trending_score, formation_evidence │
└───────────────────────────────┬──────────────────────────────────┘
                                │ enriched + clustered stories
┌───────────────────────────────▼──────────────────────────────────┐
│              MILESTONE 3: STORY INTELLIGENCE & VERIFICATION       │
│                                                                    │
│  VerificationService:                                              │
│    - Cross-publisher claim corroboration (≥ 2 sources → verified) │
│    - Conflict detection (contradictory claims → disputed flag)    │
│    - verification_score + credibility_score per story             │
│                                                                    │
│  SummaryService:                                                   │
│    - Extractive summaries (quick, beginner, professional)         │
│    - Named entity + keyword aggregation across story cluster      │
│                                                                    │
│  TimelineService:                                                  │
│    - Sub-event clustering by publish timestamp                    │
│    - Chronological StoryTimeline milestone records                │
└───────────────────────────────┬──────────────────────────────────┘
                                │ verified + scored stories
┌───────────────────────────────▼──────────────────────────────────┐
│              MILESTONE 4: RECOMMENDATION ENGINE                   │
│                                                                    │
│  PreferenceEngineService:                                          │
│    - EMA vector update on user interaction                        │
│    - Qdrant "user_preferences" → single source of truth          │
│    - Redis pref:{user_id} → hot cache (TTL 7 days)               │
│    - Postgres user_profiles → metadata pointer only              │
│                                                                    │
│  FeedAssemblerService (11-step pipeline):                          │
│    - Cold-start: SQL ORDER BY importance × trending               │
│    - Warm user: Qdrant ANN cosine vs preference vector            │
│    - Composite score + freshness decay + trending decay           │
│    - Diversity caps + mute filtering + exploration injection      │
│    - Confidence score + provenance metadata per recommendation    │
│                                                                    │
│  PreferenceUpdateWorker (async background task):                   │
│    - Positive: click, bookmark, share, dwell                      │
│    - Negative: not_interested, hide_story, mute_category/publisher│
└───────────────────────────────┬──────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────┐
│                       PERSISTENCE LAYER                           │
│                                                                    │
│  PostgreSQL (port 5433):                                           │
│    publishers, articles, stories, users, user_profiles,           │
│    user_interactions, user_recommendation_logs,                   │
│    article_duplicates, story_relations, story_timelines,          │
│    chat_sessions, chat_messages                                   │
│                                                                    │
│  Qdrant (port 6333):                                               │
│    "articles"         — per-article embeddings (384-dim COSINE)   │
│    "stories"          — story centroid embeddings (384-dim COSINE)│
│    "user_preferences" — user profile embeddings (384-dim COSINE)  │
│                                                                    │
│  Redis (port 6379):                                                │
│    pref:{user_id}     — Qdrant preference point ID (TTL 7 days)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Milestone 1 — Infrastructure & Ingestion

### Article Ingestion Pipeline

```
RSS Feed URL (feedparser)
     │
     ▼
Extract: title, body, author, published_at, source_url
     │
     ▼
html_cleaner → strip tags, normalize whitespace
     │
     ▼
SHA-256(title + body[:500]) → content_hash
     │
     ├── DUPLICATE? → discard / link as EXACT_DUPLICATE
     │
     ▼
Save Article to Postgres → dispatch for NLP enrichment
```

### Duplicate Classification

| Type | Trigger | Action |
|------|---------|--------|
| `EXACT_DUPLICATE` | Same `content_hash` | Discard; record in `article_duplicates` |
| `SEMANTIC_DUPLICATE` | cosine similarity ≥ 0.95 | Link to same story; record in `article_duplicates` |

### Publisher Registry

Every publisher has a static `credibility_score` (0.00–1.00) and `bias_rating` stored in the `publishers` table. The credibility score is aggregated into story-level scoring in Milestones 2 and 3.

---

## Milestone 2 — Semantic Intelligence

### NLP Enrichment (per Article)

| Step | Tool | Output |
|------|------|--------|
| Named Entity Recognition | spaCy `en_core_web_sm` | `named_entities` (PERSON, ORG, GPE) |
| Keyword Extraction | KeyBERT (shared SentenceTransformer) | `keywords` (top-5) |
| Topic Detection | Noun chunk frequency | `topics` (top-3) |
| Word Count / Read Time | Python string ops | `word_count`, `reading_time` |

### Category Classification (Two-Tier)

```
Article text
     │
     ▼
Tier 1: Cosine similarity vs 10 category anchor embeddings
     ├── score ≥ 0.45 → assign category
     │
     ▼
Tier 2 (fallback): keyword frequency table matching
     └── assign most-matched category
```

Categories: `Technology`, `Politics`, `Business`, `Science`, `Health`, `Sports`, `Entertainment`, `World`, `Environment`, `Crime`

### Semantic Clustering (Qdrant ANN)

```
Article embedding (384-dim)
     │
     ▼
Search "stories" collection (cosine, top-1)
     │
     ├── score > 0.82 → merge into existing Story
     │      Update: centroid (running average), importance_score,
     │              trending_score, formation_evidence, last_updated_at
     │
     └── score ≤ 0.82 → create new Story (seed centroid)
```

### Story Quality Signals

| Signal | Formula |
|--------|---------|
| `importance_score` | `0.35×article_count + 0.35×publisher_diversity + 0.20×freshness(24h) + 0.10×confidence` |
| `trending_score` | `0.40×recency(6h) + 0.30×growth_rate + 0.30×publisher_diversity` |
| `confidence_score` | Mean cosine similarity of member articles to centroid |

---

## Milestone 3 — Story Intelligence & Verification

### Verification Pipeline

```
Story (≥ 2 articles, multiple publishers)
     │
     ▼
Claim extraction → per article (rule-based NLP, no LLM)
     │
     ▼
Cross-publisher corroboration:
  ≥ 2 sources assert same claim → CORROBORATED
  Contradictory assertions      → DISPUTED (has_conflicts = True)
     │
     ▼
verification_score = corroborated_claims / total_claims
credibility_score  = weighted average publisher credibility
```

### Story Summaries (Extractive)

Three extractive summary tiers generated from cluster body text:
- `summary_quick` — 1-sentence headline summary
- `summary_beginner` — 2–3 sentence accessible summary
- `summary_professional` — 4–5 sentence analyst-grade summary

### Story Timeline Construction

New articles with distinct `published_at` timestamps trigger `StoryTimeline` milestone records:
```
Article cluster → Sub-event detection by timestamp grouping
     │
     ▼
Chronological StoryTimeline entries:
  - event_timestamp
  - headline (centroid-nearest article title)
  - description (extractive snippet)
```

---

## Milestone 4 — Recommendation Engine

### User Preference Model

Qdrant is the **single source of truth** for all user embedding vectors. Postgres stores only a pointer ID. Redis caches the pointer for sub-millisecond lookups.

```
Redis  →  pref:{user_id}  →  Qdrant point ID  →  384-dim preference vector
                                 ↑
Postgres  →  user_profiles.preference_vector_id  (fallback on cache miss)
```

### EMA Preference Updates

**Positive interaction** (click, bookmark, share, dwell):
```
P_new = (1 - α) × P_old + α × C_story
P_final = P_new / ‖P_new‖₂   (L2-normalize)
```

**Negative interaction** (not_interested, hide_story):
```
P_new = (1 + α) × P_old − α × C_story
P_final = P_new / ‖P_new‖₂
```

EMA weights by interaction type: `share=0.40`, `bookmark=0.35`, `dwell_long=0.20`, `click=0.15`, `dwell_short=0.05`

### Feed Assembly Pipeline (11 Steps)

| Step | Action |
|------|--------|
| 1 | **Candidate Retrieval** — cold-start: SQL top-60 by `importance × trending`; warm user: Qdrant ANN top-60 |
| 2 | **Live Trending Decay** — `trending_live = trending_score × 2^(-t / t_half_trend)` |
| 3 | **Composite Scoring** — `score = Ws·sem_sim + Wi·importance + Wt·trending + Wc·credibility` |
| 4 | **Freshness Decay** — `final_score = score × 2^(-t / t_half_fresh)` |
| 5 | **Negative Feedback Filter** — exclude muted categories + publishers |
| 6 | **Bucket Segmentation** — HIGH (≥0.70), MEDIUM (0.45–0.69), LOW (<0.45) |
| 7 | **Freshness Sort** — sort each bucket by `last_updated_at DESC` |
| 8 | **Multi-Axis Diversity** — caps per category, publisher, source_type |
| 9 | **Exploration Injection** — deterministic: high credibility, lowest exposure, unseen |
| 10 | **Interleave** — merge buckets 4:2:1 (HIGH:MEDIUM:LOW) |
| 11 | **24h Deduplication** — exclude stories already served in last 24 hours |

### Ranking Formula

```
composite_score = Ws·sem_sim + Wi·importance + Wt·trending + Wc·credibility
final_score     = composite_score × 2^(-t / t½)
```

Default weights: `Ws=0.50, Wi=0.25, Wt=0.15, Wc=0.10`
Default freshness half-life: `t½ = 24h`
Default trending half-life: `t½_trend = 6h`

### Recommendation Confidence

```
C = base_confidence + C_interactions + C_maturity + C_stability

base_confidence  = 0.40 (cold-start) | 0.70 (warm user)
C_interactions   = min(0.20, interaction_count × 0.01)
C_maturity       = min(0.10, profile_age_days × 0.01)
C_stability      = +0.05 if warm user AND semantic_similarity > 0.60
```

### Recommendation Provenance (per story served)

Every story recommendation persists a structured `recommendation_metadata` JSON:
```json
{
  "strategy": "personalized",
  "source": "semantic_similarity",
  "matched_story_id": "...",
  "matched_categories": ["Technology"],
  "boosts": ["freshness", "credibility"],
  "ranking_algorithm": "v1",
  "score": 0.85,
  "confidence": 0.88
}
```

### Feature Flags

| Flag | Default | Effect |
|------|---------|--------|
| `ENABLE_PERSONALIZATION` | `True` | False → all users get cold-start |
| `ENABLE_DIVERSITY` | `True` | False → no category/publisher caps |
| `ENABLE_EXPLORATION` | `True` | False → no random discovery injection |
| `ENABLE_FRESHNESS_DECAY` | `True` | False → decay multiplier = 1.0 |
| `ENABLE_TRENDING_DECAY` | `True` | False → use stored trending_score |
| `ENABLE_NEGATIVE_FEEDBACK` | `True` | False → ignore mutes |

---

## Database Schema Overview

```
publishers ─────────────── articles ──────────────── stories
                               │                        │
                               │                   story_relations (self-ref)
                               │                   story_timelines
                               │
                    article_duplicates (provenance)

users ──────── user_profiles (preference metadata)
         │──── user_interactions
         │──── user_recommendation_logs
         └──── chat_sessions ─── chat_messages
```

### Key Tables Added Per Milestone

| Table | Milestone | Purpose |
|-------|-----------|---------|
| `publishers`, `articles`, `stories` | 1 | Core content entities |
| `article_duplicates` | 1 | Deduplication provenance |
| `story_relations` | 2 | Inter-story semantic links |
| `story_timelines` | 3 | Chronological story milestones |
| `user_profiles` | 4 | Preference metadata (Qdrant pointer, mutes, drift tracking) |
| `user_recommendation_logs` | 4 | Structured feed serving audit log |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Welcome + version info |
| `GET` | `/health` | Postgres connectivity check |
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/api/v1/metrics` | Pipeline performance statistics |
| `POST` | `/api/v1/metrics/reset` | Reset metrics (dev only) |
| `GET` | `/api/v1/feed/health` | Recommendation engine diagnostics |
| `GET` | `/api/v1/feed/{user_id}` | Personalized ranked news feed |
| `POST` | `/api/v1/feed/interact` | Record user interaction (async) |
| `GET` | `/api/v1/feed/{user_id}/profile/health` | User profile diagnostics |

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

Seed test users (development):
```powershell
python scripts\seed_users.py
```

Generate analytics report:
```powershell
python scripts\generate_analytics.py
```

See `docs\recommendation-engine.md` for the full Milestone 4 technical reference.

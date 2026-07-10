# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning: [Semantic Versioning](https://semver.org/).

## [0.5.0] — 2026-07-10 — Conversational RAG Q&A Engine

### Added
- **Provider-Agnostic LLM Layer:**
  - Decoupled RAG pipeline from model SDKs using a clean `BaseLLMProvider` interface.
  - Implemented `GeminiProvider` using Google Generative AI free-tier.
  - Implemented `MockProvider` supporting offline test executions and smart source-citation generation.
- **Isolated RAG Coordination:**
  - Implemented `RAGService` coordinating embedding encoding, Qdrant searches, context formatting, and citation parsing.
  - Created `RAGChunker` to segment texts into character windows of 1500 with a 300 character overlap.
- **No-Context Optimization:**
  - Skips LLM provider calls when Qdrant returns 0 chunks above the relevance threshold, returning a deterministic fallback.
- **Response Confidence & Citations:**
  - Computes answer confidence mathematically from context similarities, retrieved counts, character coverage, and citations.
  - Extracts `[Source: Publisher Name]` citations from response text and maps them back to database article records.
- **Database Schema Enhancements:**
  - Extended `ChatSession` model with `title` and `message_count`. Added title auto-generation from first user message.
  - Extended `ChatMessage` model with `prompt_version` and `chat_metadata` columns.
- **Alembic Migration `6b10a5e8f8dc`:**
  - Manual migration script applying database changes for conversational AI.
- **Conversational Health Diagnostics:**
  - `GET /api/v1/chat/health` reporting model types, prompt versions, active sessions, and engine latencies.
- **Expanded Analytics Script:**
  - Updated `generate_analytics.py` to seed chat entries and compile Section 13 (Conversational AI & RAG Analytics) in `dataset_analytics_report.md`.
- **Comprehensive Unit Tests:**
  - Added 20 new tests in `tests/test_chat.py` verifying RAG logic, confidence scores, providers, SSE streaming, and health stats. All 20 tests pass.
- **Type Safety & Linters:**
  - Passed all `ruff` check and `mypy` type correctness checks with zero warnings/errors.

---

## [0.4.0] — 2026-07-09 — Recommendation Engine (with Refined Architecture)

### Added
- **Recommendation Confidence & Provenance:**
  - Calculates confidence score ($C \in [0, 1]$) based on warm state, interaction count, profile maturity age, and semantic similarity stability.
  - Stores structured explanation provenance inside metadata: `strategy`, `source`, `matched_story_id`, `matched_categories`, `boosts`, `ranking_algorithm`.
- **Ranking Version Tracking:**
  - Persists `ranking_version = "v1"` setting in each `UserRecommendationLog` database record for algorithm testing.
- **Smarter Exploration Strategy:**
  - Injects high credibility (`credibility_score >= 0.8`), low exposure (lowest `article_count` ascending), high quality (`importance_score` descending), unseen stories deterministically.
- **Recommendation Health Check Route:**
  - `GET /api/v1/feed/health` endpoint returning Redis status, Qdrant status, average latencies, cache hit/miss ratio, active feature flags, ranking version, profile states, and engine availability.
- **Enhanced Analytics Compilation:**
  - Expanded script to calculate and export Shannon category entropy, confidence statistics, latencies, hit ratios, and source distribution in Section 12.
- **Profile Drift Columns:**
  - Prepared `user_profiles` schema with `profile_age_days`, `last_profile_decay`, `last_profile_rebuild`, and `last_profile_update` columns.
- **Full Test Suite & Linters:**
  - Added 6 new tests in `test_recommendation.py` (total 26 passed tests).
  - 100% clean check on Ruff and MyPy.
- **Alembic Migration `5a09b4d8d1cf`:** Applied schema updates for profile drift and ranking version columns.

### Changed
- `UserRecommendationLog`: removed `recommendation_reason` (str), added `recommendation_metadata` (JSON), `is_personalized` (bool), `strategy` (str).
- `User` model: added `preference_vector_id`, `interaction_count`, `last_feed_at`.
- `VectorStoreService`: added `user_preferences` Qdrant collection initialization.
- `main.py`: API version `3.0.0`, `lifespan` startup hook, registered `feed_router`.
- `generate_analytics.py`: expanded to 12-section report.
- `README.md`: updated to reflect current capabilities, endpoints, and milestone progress.

---

## [0.3.0] — 2026-07-04 — Story Intelligence & Verification

### Added
- `StoryVerificationService`: deterministic multi-source fact-checking pipeline.
  - Agreement scoring, publisher diversity analysis, conflict detection.
  - Structured `verification_metadata` JSON on each `Story`.
- `StoryTimeline`: 6-hour windowed milestone generation.
- 11-section analytics report via `generate_analytics.py`.
- 36 tests in full test suite.

---

## [0.2.0] — 2026-06-28 — Semantic Intelligence

### Added
- Sentence-transformer embedding pipeline (`all-MiniLM-L6-v2`, 384-dim).
- `ClusteringService`: cosine similarity story clustering with Qdrant ANN.
- Story importance and trending score computation.
- Formation evidence JSON (XAI cluster membership explanation).
- RAG context payload on `Story` entities.
- Duplicate detection: EXACT_DUPLICATE and SEMANTIC_DUPLICATE classification.

---

## [0.1.0] — 2026-06-27 — Infrastructure & Ingestion

### Added
- FastAPI backend with async SQLAlchemy + asyncpg.
- PostgreSQL, Redis, Qdrant — all containerized in Docker.
- Alembic migration framework.
- RSS ingestion pipeline for 12 publishers.
- spaCy NER + KeyBERT keyword extraction.
- `MetricsService`: per-phase pipeline performance tracking.

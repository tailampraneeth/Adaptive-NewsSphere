# Engineering & Design Decisions: Adaptive NewsSphere Backend

This document details the architectural choices, framework selections, and design patterns established during the development of **Adaptive NewsSphere (ANS)** backend. It is designed to help engineers, reviewers, and recruiters understand the rationale behind the system's architecture.

---

## 1. Modular Monolith over Microservices

### Decision
Adaptive NewsSphere is structured as a **Modular Monolith** rather than a distributed set of microservices.

### Rationale
*   **Single Developer Velocity:** Eliminates network orchestration overhead, distributed tracing complexity, and repository synchronization friction.
*   **Resource Efficiency:** Fits cleanly within a developer's local machine or a standard CI/CD pipeline, avoiding the footprint of multiple service runtimes.
*   **Logical Isolation:** Clean boundaries are maintained via decoupled service layers (`IngestionService`, `ClusteringService`, `CategoryClassifierService`), allowing easy transition to microservices if scale demands it in the future.

---

## 2. Framework & Library Selections

### FastAPI
*   **Asynchronous Core:** Native support for `async/await` allows handling concurrent RSS feed ingestion and database writes with minimal thread blocking.
*   **Self-Documenting API:** Out-of-the-box OpenAPI (Swagger) generation simplifies API exploration for frontend development and external reviews.
*   **Performance:** Consistently ranks among the fastest Python web frameworks, matching the throughput of Node.js and Go for I/O-bound tasks.

### SQLAlchemy 2.0 (with Asyncpg)
*   **Type Safety & Mappings:** Native PEP 484 type integration via `Mapped` columns prevents runtime database schema type errors.
*   **Connection Control:** Configured with `NullPool` in tests to ensure database connections are cleanly disposed of, avoiding "operation in progress" blocks during schema setups.

### Qdrant Vector Database
*   **High Performance:** Written in Rust, providing low-latency similarity queries and centroid retrieval.
*   **Local Portability:** Easily containerized via Docker, allowing semantic searches without relying on paid, cloud-only endpoints (e.g., Pinecone).

### Sentence-Transformers (`all-MiniLM-L6-v2`)
*   **Free & Local Execution:** Embedding generation occurs entirely on-device, keeping the backend free of API dependencies (like OpenAI).
*   **Optimal Balance:** At 384 dimensions, it offers fast cosine-similarity comparisons in Qdrant while preserving strong semantic relationships between news headlines.

---

## 3. Database Schema: Resolving Circular Dependencies

### Problem
In Milestone 2, we introduced:
1.  `Article` table referencing `Story.id` (`story_id`) to map articles to their semantic story.
2.  `Story` table referencing `Article.id` (`representative_article_id`) to denote the centroid-nearest representative article.

This caused a circular foreign key constraint dependency, resulting in `CircularDependencyError` when dropping or creating tables.

### Solution
We resolved this by:
*   Configuring the `representative_article_id` foreign key in `Story` with `use_alter=True` and an explicit constraint name (`fk_stories_representative_article`).
*   This instructs SQLAlchemy and Alembic to create the foreign key using an `ALTER TABLE` statement *after* both tables are created, and drop it via `ALTER TABLE` *before* dropping tables.
*   Explicitly linking both relationships using `foreign_keys` specifications on both model sides (`[Article.story_id]` and `[Story.representative_article_id]`) to prevent mapper collision.

---

## 4. Multi-Tier Category Classification Priority

To eliminate "Uncategorized" metadata, the classifier service applies a strict four-tiered hierarchy:
1.  **Original RSS Metadata:** Reuses publisher-assigned tags if available.
2.  **Nearest Neighbor Search:** Queries Qdrant for similar articles. If a match has similarity $\ge 0.80$, we inherit its category.
3.  **Pre-computed Centroid Anchors:** Generates text embeddings and computes cosine similarity against pre-computed category centroids (confidence $\ge 0.45$).
4.  **Keyword Heuristics:** Falls back to keyword frequency map counts if embedding confidence is low.

---

## 5. Duplicate Article Taxonomy

To represent the lifecycle of news updates and corrections, duplicates are classified into four precise states:
*   **`EXACT_DUPLICATE`:** Identical content hash. Handled by linking to the parent story and penalizing `quality_score` by 50%.
*   **`SEMANTIC_DUPLICATE`:** Similarity score $\ge 0.95$ to an existing article. Linked via `ArticleDuplicate` and penalized by 50%.
*   **`UPDATED_ARTICLE`:** Identical URL but modified content hash. Linked to the original story with a versioned hash link.
*   **`CORRECTED_ARTICLE`:** Similarity $\ge 0.85$ from the same publisher with clear correction keywords (e.g., "clarification", "correction", "amended").

---

## 6. Feed Health & Latency Metrics

Rather than manual tracking, feed performance metrics are updated automatically within the `IngestionService` pipeline on every fetch:
*   **Fetch Success/Failure Rates:** Stored directly on the `Publisher` database record.
*   **Duplicate Rates:** Kept as a percentage to flag spammy or stale feeds.
*   **Latency Moving Averages:** Tracks server response speeds to dynamically monitor feed health.

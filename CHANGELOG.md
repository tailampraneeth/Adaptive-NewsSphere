# Changelog

All notable changes to the Adaptive NewsSphere project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and adheres to Semantic Versioning.

## [1.5.0] - 2026-06-27
### Added
- Expanded RSS news collection crawler supporting 12 publishers (BBC, Wired, TechCrunch, Verge, The Guardian, TechRadar, Reuters, AP, MIT Tech Review, Ars Technica, CNBC, The Hindu).
- Integrations for spaCy Named Entity Recognition (`PERSON`, `ORG`, `GPE`).
- KeyBERT keyword extraction sharing sentence-transformer instances to save CPU/RAM.
- Heuristic topic extraction and word/reading count metrics.
- Multi-collection Qdrant vector database service mapped to port `6333`.
- Distance.COSINE similarity clustering engine linking articles to Story entities.
- Feed quality analytics and automated data quality validation gates.
- Repository professionalization documents (MIT License, Contributing Guidelines, Changelog, Code of Conduct, Security Policy).

## [1.0.0] - 2026-06-26
### Added
- Core backend framework with FastAPI.
- Alembic database migration manager.
- PostgreSQL database infrastructure containerized in Docker.
- Redis cache broker containerized in Docker.
- Basic RSS feed parser ingestion unit.

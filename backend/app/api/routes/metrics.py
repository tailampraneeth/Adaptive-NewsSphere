"""
Metrics API router — exposes the MetricsService performance data over HTTP.

Endpoint:
  GET /api/v1/metrics
    Returns per-phase timing statistics for the current process lifetime.

Response shape:
  {
    "phases": {
      "embedding_generate": {"count": 42, "avg_ms": 12.5, "min_ms": 8.1, "max_ms": 21.3, "total_ms": 525.0},
      "story_cluster":      {"count": 38, ...},
      ...
    },
    "recorded_at": "2026-06-28T00:00:00Z"
  }
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.services.metrics import get_metrics

router = APIRouter(prefix="/api/v1", tags=["observability"])


@router.get("/metrics", summary="Pipeline performance metrics")
def get_pipeline_metrics() -> dict:
    """
    Returns real-time aggregated performance statistics for all pipeline phases.

    Phases tracked:
      - rss_fetch, html_clean, nlp_extract
      - embedding_generate, qdrant_index, similarity_search
      - story_cluster, category_classify

    Metrics reset on process restart.
    """
    metrics = get_metrics()
    return {
        "phases": metrics.get_summary(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/metrics/reset", summary="Reset pipeline metrics (dev only)")
def reset_pipeline_metrics() -> dict:
    """Clears all accumulated metrics. Intended for testing and development."""
    metrics = get_metrics()
    metrics.reset()
    return {"status": "ok", "message": "Metrics reset successfully."}

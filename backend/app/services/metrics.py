"""
MetricsService — Lightweight in-process performance tracking.

Records execution durations for each processing phase in the pipeline.
Provides aggregated statistics without any external dependencies (no Prometheus,
no StatsD, no database writes).

Tracked phases:
  rss_fetch         — RSS feed network fetch
  html_clean        — HTML stripping and content extraction
  nlp_extract       — spaCy NER + KeyBERT + topic extraction
  embedding_generate — SentenceTransformer encode
  qdrant_index      — Qdrant upsert operation
  similarity_search — Qdrant similarity search
  story_cluster     — Full ClusteringService.cluster_article call
  category_classify — CategoryClassifierService.classify

Usage:
  metrics = MetricsService()
  metrics.record("embedding_generate", 12.5)
  summary = metrics.get_summary()
  # → { "embedding_generate": { "count": 1, "total_ms": 12.5, "avg_ms": 12.5, "min_ms": 12.5, "max_ms": 12.5 } }

Thread safety:
  Uses a simple dict with no locking. Suitable for single-threaded async
  FastAPI workers. For multi-threaded environments, add threading.Lock.
"""
import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Dict, Generator

logger = logging.getLogger("adaptive-newssphere.metrics")


class MetricsService:
    """
    In-memory performance metrics accumulator.

    Maintains per-phase statistics:
      count     — total number of recorded operations
      total_ms  — cumulative execution time in milliseconds
      avg_ms    — running average
      min_ms    — minimum observed latency
      max_ms    — maximum observed latency

    The metrics are stored per process lifetime and reset on restart.
    """

    def __init__(self) -> None:
        # phase → {"count": int, "total_ms": float, "min_ms": float, "max_ms": float}
        self._data: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "total_ms": 0.0, "min_ms": float("inf"), "max_ms": 0.0}
        )

    def record(self, phase: str, duration_ms: float, metadata: Dict | None = None) -> None:
        """
        Records a single operation duration for the given phase.

        Args:
          phase: Named pipeline phase (e.g. "embedding_generate")
          duration_ms: Operation duration in milliseconds
          metadata: Optional extra context (logged at DEBUG level, not stored)
        """
        bucket = self._data[phase]
        bucket["count"] += 1
        bucket["total_ms"] += duration_ms
        bucket["min_ms"] = min(bucket["min_ms"], duration_ms)
        bucket["max_ms"] = max(bucket["max_ms"], duration_ms)

        if metadata:
            logger.debug(f"[metrics] {phase}: {duration_ms:.2f}ms | {metadata}")

    @contextmanager
    def measure(self, phase: str, metadata: Dict | None = None) -> Generator[None, None, None]:
        """
        Context manager that automatically records duration.

        Example:
          with metrics.measure("embedding_generate"):
              vector = model.encode(text)
        """
        t0 = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - t0) * 1000
            self.record(phase, duration_ms, metadata)

    def get_summary(self) -> Dict:
        """
        Returns aggregated statistics for all recorded phases.

        Returns:
          {
            "phase_name": {
              "count": int,
              "total_ms": float,
              "avg_ms": float,
              "min_ms": float,
              "max_ms": float
            },
            ...
          }
        """
        summary: Dict = {}
        for phase, bucket in self._data.items():
            count = int(bucket["count"])
            total = bucket["total_ms"]
            summary[phase] = {
                "count": count,
                "total_ms": round(total, 2),
                "avg_ms": round(total / count, 2) if count > 0 else 0.0,
                "min_ms": round(bucket["min_ms"], 2) if count > 0 else 0.0,
                "max_ms": round(bucket["max_ms"], 2),
            }
        return summary

    def reset(self) -> None:
        """Clears all accumulated metrics. Useful for testing."""
        self._data.clear()


# Module-level singleton — shared across FastAPI request handlers
_metrics_instance: MetricsService | None = None


def get_metrics() -> MetricsService:
    """Returns the global MetricsService singleton, creating it on first call."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsService()
    return _metrics_instance

"""
Tests for MetricsService — M2 Final Engineering Review.

Covers:
  - record() accumulates count, total, min, max correctly
  - get_summary() returns correct averages
  - measure() context manager records duration automatically
  - reset() clears all data
  - Multiple phases are tracked independently
  - get_metrics() singleton returns the same instance
"""
import time
import pytest
from app.services.metrics import MetricsService, get_metrics


@pytest.fixture()
def metrics() -> MetricsService:
    """Fresh MetricsService instance for each test (not the singleton)."""
    return MetricsService()


def test_record_single_operation(metrics: MetricsService):
    """Single record should produce correct stats."""
    metrics.record("embedding_generate", 15.5)
    summary = metrics.get_summary()
    assert "embedding_generate" in summary
    phase = summary["embedding_generate"]
    assert phase["count"] == 1
    assert phase["total_ms"] == 15.5
    assert phase["avg_ms"] == 15.5
    assert phase["min_ms"] == 15.5
    assert phase["max_ms"] == 15.5


def test_record_multiple_operations(metrics: MetricsService):
    """Multiple records should accumulate correctly."""
    metrics.record("qdrant_index", 10.0)
    metrics.record("qdrant_index", 20.0)
    metrics.record("qdrant_index", 30.0)
    summary = metrics.get_summary()
    phase = summary["qdrant_index"]
    assert phase["count"] == 3
    assert phase["total_ms"] == 60.0
    assert phase["avg_ms"] == 20.0
    assert phase["min_ms"] == 10.0
    assert phase["max_ms"] == 30.0


def test_independent_phases(metrics: MetricsService):
    """Different phases should be tracked independently."""
    metrics.record("nlp_extract", 50.0)
    metrics.record("embedding_generate", 12.0)
    summary = metrics.get_summary()
    assert "nlp_extract" in summary
    assert "embedding_generate" in summary
    assert summary["nlp_extract"]["count"] == 1
    assert summary["embedding_generate"]["count"] == 1
    assert summary["nlp_extract"]["avg_ms"] == 50.0
    assert summary["embedding_generate"]["avg_ms"] == 12.0


def test_measure_context_manager(metrics: MetricsService):
    """measure() context manager should record positive duration automatically."""
    with metrics.measure("similarity_search"):
        time.sleep(0.01)  # 10ms

    summary = metrics.get_summary()
    assert "similarity_search" in summary
    phase = summary["similarity_search"]
    assert phase["count"] == 1
    assert phase["total_ms"] > 0.0, "Should record a positive duration"
    assert phase["total_ms"] < 500.0, "Should not take more than 500ms for a 10ms sleep"


def test_reset_clears_all_data(metrics: MetricsService):
    """reset() should clear all phase data."""
    metrics.record("rss_fetch", 100.0)
    metrics.record("html_clean", 5.0)
    metrics.reset()
    summary = metrics.get_summary()
    assert len(summary) == 0, "Summary should be empty after reset"


def test_empty_summary_on_new_instance(metrics: MetricsService):
    """Fresh MetricsService should return empty summary."""
    summary = metrics.get_summary()
    assert summary == {}


def test_get_metrics_returns_singleton():
    """get_metrics() should return the same instance on repeated calls."""
    m1 = get_metrics()
    m2 = get_metrics()
    assert m1 is m2, "get_metrics() should return a singleton"


def test_metadata_parameter_does_not_crash(metrics: MetricsService):
    """Passing metadata to record() should not raise any exceptions."""
    metrics.record("story_cluster", 88.0, metadata={"story_id": "abc123", "path": "new"})
    summary = metrics.get_summary()
    assert summary["story_cluster"]["count"] == 1

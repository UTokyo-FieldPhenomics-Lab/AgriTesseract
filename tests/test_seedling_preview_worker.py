"""Tests for preview worker error formatting."""

from src.utils.seedling_detect.qthread import format_worker_exception


def test_format_worker_exception_includes_traceback_lines() -> None:
    """Worker exception formatter should include exception type and traceback."""
    try:
        raise RuntimeError("sam3 boom")
    except RuntimeError as exc:
        message = format_worker_exception(exc)
    assert "RuntimeError" in message
    assert "sam3 boom" in message
    assert "Traceback" in message

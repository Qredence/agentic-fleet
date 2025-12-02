import logging
from contextlib import contextmanager

from agentic_fleet.app.main import _configure_logging
from agentic_fleet.app.settings import get_settings


@contextmanager
def preserve_handlers():
    root = logging.getLogger()
    original = list(root.handlers)
    try:
        yield
    finally:
        root.handlers = original


def test_json_logging_enabled(monkeypatch):
    monkeypatch.setenv("LOG_JSON", "1")
    get_settings.cache_clear()
    with preserve_handlers():
        _configure_logging()
        handler = logging.getLogger().handlers[-1]
        # JsonFormatter inherits from logging.Formatter; check class name to avoid import coupling
        assert handler.formatter.__class__.__name__ == "JsonFormatter"

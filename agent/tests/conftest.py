"""Keep fixture tests independent of a developer's private service settings."""

import os

import pytest

from gopstop_agent.config import Settings


def pytest_configure(config):
    # Run before collection: importing main constructs its default app/settings.
    monkeypatch = pytest.MonkeyPatch()
    config.add_cleanup(monkeypatch.undo)
    for name in list(os.environ):
        if name.startswith("AGENT_") or name in {
            "ANTHROPIC_API_KEY", "GROQ_API_KEY", "EXA_API_KEY", "SPRING_DATA_REDIS_URL",
        }:
            monkeypatch.delenv(name)
    monkeypatch.setitem(Settings.model_config, "env_file", None)

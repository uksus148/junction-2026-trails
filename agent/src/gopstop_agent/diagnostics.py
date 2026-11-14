"""Correlate internal stages without logging messages, keys or raw session IDs."""

import hashlib
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4


log = logging.getLogger(__name__)
current = ContextVar("chat_trace", default=None)


@contextmanager
def trace(session_id: str):
    token = current.set((uuid4().hex[:12], hashlib.sha256(session_id.encode()).hexdigest()[:12]))
    try:
        yield
    finally:
        current.reset(token)


@contextmanager
def stage(name: str):
    started, outcome = time.monotonic(), "ok"
    try:
        yield
    except BaseException as exc:
        outcome = type(exc).__name__
        raise
    finally:
        if current.get() is not None:
            request, session = current.get()
            log.info("chat trace=%s session=%s stage=%s elapsed_ms=%.0f outcome=%s",
                     request, session, name, (time.monotonic() - started) * 1000, outcome)

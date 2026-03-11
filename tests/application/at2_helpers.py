# index-retriever-mcp-server — AT2 Helpers
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared helpers for W23A application-level backend/parser/embedding matrix tests.

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from tests.live_runtime import LiveIndexRuntime, resolve_live_runtime_config


@contextmanager
def temporary_env(overrides: dict[str, str]) -> Iterator[None]:
    saved: dict[str, str | None] = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_live_runtime() -> LiveIndexRuntime:
    resolve_live_runtime_config.cache_clear()
    return LiveIndexRuntime()

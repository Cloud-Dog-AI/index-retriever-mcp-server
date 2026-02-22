# index-retriever-mcp-server — VDB Registry
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Registry for vector backend adapters.

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class VdbRegistry:
    """Lookup table for vector backend factory callables."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self._factories: dict[str, Callable[[], Any]] = {}

    def register(self, backend_type: str, factory: Callable[[], Any]) -> None:
        """Execute register."""
        self._factories[backend_type] = factory

    def get(self, backend_type: str) -> Any:
        """Execute get."""
        if backend_type not in self._factories:
            raise KeyError(f"Unsupported vector backend: {backend_type}")
        return self._factories[backend_type]()

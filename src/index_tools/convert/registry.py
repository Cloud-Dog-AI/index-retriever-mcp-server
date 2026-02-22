# index-retriever-mcp-server — Converter Registry
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Registry for selecting conversion backends by file type.

from __future__ import annotations

from collections.abc import Callable

Converter = Callable[[bytes], str]


class ConverterRegistry:
    """Registry mapping file extensions to converter callables."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self._converters: dict[str, Converter] = {}

    def register(self, extension: str, converter: Converter) -> None:
        """Execute register."""
        self._converters[extension.lower().strip()] = converter

    def select(self, extension: str) -> Converter:
        """Execute select."""
        key = extension.lower().strip()
        if key in self._converters:
            return self._converters[key]
        if "*" in self._converters:
            return self._converters["*"]
        raise KeyError(f"No converter registered for extension: {extension}")

# index-retriever-mcp-server — Redis Bridge
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Optional Redis/Valkey queue multiplier bridge.

from __future__ import annotations


class RedisBridge:
    """Optional queue bridge placeholder used for runtime toggling."""

    def __init__(self, enabled: bool, url: str = "") -> None:
        self.enabled = enabled
        self.url = url

    def status(self) -> str:
        if self.enabled:
            return "enabled"
        return "disabled"

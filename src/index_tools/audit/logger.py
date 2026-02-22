# index-retriever-mcp-server — Audit Logger
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: JSONL audit logger with secret redaction.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from index_tools.audit.events import AuditEvent

try:
    import cloud_dog_logging  # type: ignore
except ImportError:  # pragma: no cover - fallback for local development only
    cloud_dog_logging = None


REDACT_KEYS = {
    "api_key",
    "token",
    "password",
    "secret",
    "access_key",
    "private_key",
    "authorization",
}


def redact_payload(value: Any) -> Any:
    """Recursively redact secret fields in audit payloads."""
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, nested in value.items():
            if key.lower() in REDACT_KEYS:
                output[key] = "[REDACTED]"
            else:
                output[key] = redact_payload(nested)
        return output
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value


class AuditLogger:
    """Append-only JSONL audit logger."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: AuditEvent) -> None:
        payload = redact_payload(event.model_dump(mode="json"))
        line = json.dumps(payload, ensure_ascii=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def get_backend_name(self) -> str:
        if cloud_dog_logging is not None:
            return "cloud_dog_logging"
        return "jsonl-fallback"

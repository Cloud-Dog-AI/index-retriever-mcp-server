# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        """Initialise the instance state."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: AuditEvent) -> None:
        """Execute write event."""
        # Covers: FR-06
        payload = redact_payload(event.model_dump(mode="json"))
        line = json.dumps(payload, ensure_ascii=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def get_backend_name(self) -> str:
        """Execute get backend name."""
        if cloud_dog_logging is not None:
            return "cloud_dog_logging"
        return "jsonl-fallback"

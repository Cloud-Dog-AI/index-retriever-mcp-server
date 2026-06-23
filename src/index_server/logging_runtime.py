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

import contextlib
import socket
from typing import Any

from cloud_dog_logging import setup_logging  # type: ignore

from index_tools.config.loader import runtime_env_files

_KNOWN_SURFACES = frozenset({"api_server", "web_server", "mcp_server", "a2a_server"})


class _FallbackConfig:
    def get(self, _path: str, default: Any = None) -> Any:
        return default


def build_platform_log_config(config: Any, *, surface_name: str) -> dict[str, Any]:
    """Build the cloud_dog_logging config for one server surface."""
    if surface_name not in _KNOWN_SURFACES:
        raise ValueError(f"Unsupported logging surface: {surface_name}")

    surface_log = config.get(f"log.{surface_name}_log") or config.get("log.app_log")
    return {
        "service_name": str(config.get("service.name", "index-retriever-mcp-server")),
        "service_instance": (
            str(config.get("log.service_instance", "") or config.get("service.server_id", "")).strip()
            or socket.gethostname()
        ),
        "environment": str(config.get("log.environment", "") or config.get("service.environment", "dev")).strip()
        or "dev",
        "log": {
            "level": str(config.get("log.level", "INFO")),
            "format": str(config.get("log.format", "json")),
            "console": bool(config.get("log.console", True)),
            "app_log": surface_log,
            "audit_log": config.get("log.audit_log"),
            "rotation": {
                "mode": str(config.get("log.rotation.mode", "size")),
                "max_bytes": int(config.get("log.rotation.max_bytes", 104857600)),
                "backup_count": int(config.get("log.rotation.backup_count", 10)),
                "when": str(config.get("log.rotation.when", "midnight")),
                "interval": int(config.get("log.rotation.interval", 1)),
                "compress": bool(config.get("log.rotation.compress", True)),
            },
            "integrity": {
                "enabled": bool(config.get("log.integrity.enabled", True)),
                "interval_seconds": int(config.get("log.integrity.interval_seconds", 300)),
                "log_file": str(config.get("log.integrity.log_file", "logs/audit-integrity.log")),
                "hash_algorithm": str(config.get("log.integrity.hash_algorithm", "sha256")),
            },
            "retention": {
                "hot_days": int(config.get("log.retention.hot_days", 14)),
                "cold_days": int(config.get("log.retention.cold_days", 60)),
                "archive_format": str(config.get("log.retention.archive_format", "gz")),
            },
        },
    }


def init_platform_logging(surface_name: str) -> None:
    """Initialise cloud_dog_logging for the requested server surface."""
    # req: FR-005
    from cloud_dog_config import load_config  # type: ignore

    try:
        config = load_config(env_files=runtime_env_files(), unresolved_policy="strict")
    except Exception:
        config = _FallbackConfig()
    setup_logging(build_platform_log_config(config, surface_name=surface_name))


def shutdown_platform_logging() -> None:
    """Stop platform logging background workers before process streams close."""
    try:
        import cloud_dog_logging  # type: ignore

        shutdown_integrity_verifier = cloud_dog_logging._shutdown_integrity_verifier  # type: ignore[attr-defined]
    except Exception:
        return
    shutdown_integrity_verifier()
    with contextlib.suppress(Exception):
        cloud_dog_logging._integrity_verifier = None  # type: ignore[attr-defined]

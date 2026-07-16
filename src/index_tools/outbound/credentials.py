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

"""Config and credential resolution for outbound peer calls."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import cloud_dog_config  # type: ignore

from index_tools.config.loader import runtime_env_files

API_KEY_HEADER = "X-API-Key"
CORRELATION_HEADER = "X-Correlation-Id"
TRACEPARENT_HEADER = "traceparent"
DEFAULT_MCP_PATH = "/mcp"
DEFAULT_A2A_TASKS_PATH = "/a2a/tasks"


@dataclass(frozen=True, slots=True)
class OutboundServiceConfig:
    """Resolved non-secret outbound service configuration."""

    service_name: str
    base_url: str = ""
    mcp_url: str = ""
    a2a_url: str = ""
    mcp_path: str = DEFAULT_MCP_PATH
    tasks_path: str = DEFAULT_A2A_TASKS_PATH
    credential_header: str = API_KEY_HEADER
    credential_config_key: str = ""
    bearer_config_key: str = ""
    timeout_seconds: float = 30.0

    @property
    def resolved_mcp_url(self) -> str:
        """Return the URL used for MCP transport construction."""
        return (self.mcp_url or self.base_url).strip().rstrip("/")

    @property
    def resolved_a2a_url(self) -> str:
        """Return the URL used for A2A task and discovery calls."""
        value = (self.a2a_url or self.base_url).strip().rstrip("/")
        if value.endswith("/a2a"):
            value = value[: -len("/a2a")]
        return value


class OutboundServiceResolver:
    """Resolve peer endpoints and credentials via cloud_dog_config at call time."""

    def __init__(self, value_provider: Callable[[str], Any] | None = None) -> None:
        """Initialise a resolver with an optional test value provider."""
        self._value_provider = value_provider

    def resolve(self, service_name: str, *, transport: str = "mcp") -> OutboundServiceConfig:
        """Resolve non-secret endpoint settings for one peer service."""
        aliases = service_aliases(service_name)
        base_url = _first_text(self._lookup_candidates(aliases, ("uri", "url", "base_url")))
        mcp_url = _first_text(self._lookup_candidates(aliases, ("mcp_url", "mcp_uri"))) or base_url
        a2a_url = _first_text(self._lookup_candidates(aliases, ("a2a_url", "a2a_uri"))) or base_url
        mcp_path = (
            _first_text(self._lookup_candidates(aliases, ("mcp_path",)))
            or _config_text("outbound.mcp.path", DEFAULT_MCP_PATH, self._value_provider)
            or DEFAULT_MCP_PATH
        )
        tasks_path = (
            _first_text(self._lookup_candidates(aliases, ("tasks_path", "a2a_tasks_path")))
            or _config_text("outbound.a2a.tasks_path", DEFAULT_A2A_TASKS_PATH, self._value_provider)
            or DEFAULT_A2A_TASKS_PATH
        )
        credential_config_key = _first_text(self._lookup_candidates(aliases, ("credential_config_key",)))
        bearer_config_key = _first_text(self._lookup_candidates(aliases, ("bearer_config_key",)))
        credential_header = (
            _first_text(self._lookup_candidates(aliases, ("credential_header",)))
            or API_KEY_HEADER
        )
        timeout_default_key = "outbound.a2a.timeout_seconds" if transport == "a2a" else "outbound.mcp.timeout_seconds"
        timeout_seconds = _config_float(timeout_default_key, 30.0, self._value_provider)
        service_timeout = _first_text(self._lookup_candidates(aliases, ("timeout_seconds",)))
        if service_timeout:
            try:
                timeout_seconds = float(service_timeout)
            except ValueError:
                timeout_seconds = 30.0
        return OutboundServiceConfig(
            service_name=service_name,
            base_url=base_url,
            mcp_url=mcp_url,
            a2a_url=a2a_url,
            mcp_path=mcp_path,
            tasks_path=tasks_path,
            credential_header=credential_header,
            credential_config_key=credential_config_key,
            bearer_config_key=bearer_config_key,
            timeout_seconds=max(1.0, timeout_seconds),
        )

    def headers(
        self,
        config: OutboundServiceConfig,
        *,
        correlation_id: str,
        traceparent: str = "",
    ) -> dict[str, str]:
        """Build per-call headers, resolving credential values only for this call."""
        headers = {
            "Accept": "application/json, text/event-stream",
            CORRELATION_HEADER: correlation_id,
        }
        if traceparent:
            headers[TRACEPARENT_HEADER] = traceparent

        credential_value = self.resolve_credential(config)
        if credential_value:
            headers[config.credential_header or API_KEY_HEADER] = credential_value

        bearer_value = self.resolve_bearer(config)
        if bearer_value:
            headers["authorization"] = f"Bearer {bearer_value}"
        return headers

    def resolve_credential(self, config: OutboundServiceConfig) -> str:
        """Resolve the configured key/header credential for one call."""
        candidates: list[str] = []
        if config.credential_config_key:
            candidates.append(config.credential_config_key)
        for alias in service_aliases(config.service_name):
            candidates.extend(
                [
                    f"outbound.services.{alias}.credential",
                    f"dev.services.{alias}.api_key",
                    f"dev.services.{alias}.credential",
                ]
            )
        return _first_text(_config_value(path, "", self._value_provider) for path in candidates)

    def resolve_bearer(self, config: OutboundServiceConfig) -> str:
        """Resolve a configured bearer credential for one call."""
        if config.bearer_config_key:
            return _config_text(config.bearer_config_key, "", self._value_provider)
        for alias in service_aliases(config.service_name):
            value = _config_text(f"dev.services.{alias}.bearer_token", "", self._value_provider)
            if value:
                return value
        return ""

    def _lookup_candidates(self, aliases: list[str], suffixes: tuple[str, ...]) -> list[Any]:
        values: list[Any] = []
        for alias in aliases:
            for suffix in suffixes:
                values.append(_config_value(f"outbound.services.{alias}.{suffix}", "", self._value_provider))
                values.append(_config_value(f"dev.services.{alias}.{suffix}", "", self._value_provider))
        return values


def service_aliases(service_name: str) -> list[str]:
    """Return config-key aliases for a peer service name."""
    cleaned = str(service_name or "").strip()
    if not cleaned:
        return []
    underscore = cleaned.replace("-", "_")
    compact = underscore.replace("_", "")
    dashed = underscore.replace("_", "-")
    aliases = [cleaned, underscore, dashed, compact]
    if compact and not compact[-1:].isdigit():
        aliases.append(f"{compact}0")
    output: list[str] = []
    for alias in aliases:
        if alias and alias not in output:
            output.append(alias)
    return output


def _config_text(path: str, default: str, value_provider: Callable[[str], Any] | None) -> str:
    return str(_config_value(path, default, value_provider) or default).strip()


def _config_float(path: str, default: float, value_provider: Callable[[str], Any] | None) -> float:
    raw = _config_value(path, default, value_provider)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _config_value(path: str, default: Any, value_provider: Callable[[str], Any] | None) -> Any:
    if value_provider is not None:
        try:
            value = value_provider(path)
            return default if value is None else value
        except Exception:
            return default
    try:
        value = cloud_dog_config.get_config(path)
        return default if value is None else value
    except Exception:
        pass
    try:
        compiled = cloud_dog_config.load_config(
            env_files=runtime_env_files(),
            defaults_yaml="defaults.yaml",
            unresolved_policy="empty",
            vault_enabled=True,
        )
        value = compiled.get(path)
        return default if value is None else value
    except Exception:
        return default


def _first_text(values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""

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

"""Config-driven parser-service defaults (W28M-1626).

`cloud_dog_vdb.build_parser_registry` only registers a live parser provider
(MinerU / Marker / Docling) when the caller supplies its ``base_url``. Prior to
W28M-1626 the index-retriever service passed **no** default, so a
``structure_extract`` / ingestion call with ``provider="mineru"`` failed unless
every caller hardcoded the MinerU endpoint — a hardcoded-operational-value bypass
(RULES §2.4) which meant no country-report was ever structure-extracted live.

This module assembles the ``parser_services`` mapping from ``cloud_dog_config``
(Vault ``dev.services.mineru.uri`` surfaced as
``CLOUD_DOG__INDEX__PARSERS__MINERU__BASE_URL`` in the deployed container), so
``provider="mineru"`` works by configuration with zero hardcoding. All reads go
through ``cloud_dog_config`` — never ``os.environ`` (RULES §1.4.1).
"""

from __future__ import annotations

from typing import Any

#: Providers whose live endpoint may be defaulted from config. ``internal`` is
#: always available (offline) and needs no configuration.
_LIVE_PROVIDERS = ("mineru", "marker_mcp", "docling")


def _cfg_str(*keys: str) -> str:
    """First non-empty ``cloud_dog_config`` value across dotted / env-style keys.

    Accepts both ``index.parsers.mineru.base_url`` and
    ``CLOUD_DOG__INDEX__PARSERS__MINERU__BASE_URL`` forms; the env-style key is
    converted to its dotted equivalent and both are tried.
    """
    try:
        from cloud_dog_config import get_config
    except Exception:  # pragma: no cover - config package always present in service
        return ""
    for key in keys:
        candidates = [key]
        normalised = key
        if normalised.upper().startswith("CLOUD_DOG__"):
            normalised = normalised[len("CLOUD_DOG__"):]
        dotted = normalised.replace("__", ".").lower()
        if dotted != key:
            candidates.append(dotted)
        for candidate in candidates:
            try:
                value = get_config(candidate)
            except Exception:
                value = None
            if value is not None and str(value).strip():
                return str(value).strip()
    return ""


def _cfg_float(default: float, *keys: str) -> float:
    raw = _cfg_str(*keys)
    try:
        return float(raw) if raw else default
    except (TypeError, ValueError):
        return default


def _cfg_int(default: int, *keys: str) -> int:
    return int(_cfg_float(float(default), *keys))


def default_parser_services() -> dict[str, dict[str, Any]]:
    """Assemble default ``parser_services`` from ``cloud_dog_config``.

    A provider entry is emitted only when a ``base_url`` is configured, matching
    ``build_parser_registry`` semantics (an empty ``base_url`` leaves the provider
    unregistered). Returns an empty mapping when nothing is configured, so the
    behaviour is unchanged on deployments that do not wire a parser endpoint.
    """
    services: dict[str, dict[str, Any]] = {}

    mineru_base = _cfg_str(
        "index.parsers.mineru.base_url",
        "CLOUD_DOG__INDEX__PARSERS__MINERU__BASE_URL",
        "MINERU_BASE_URL",
        "services.mineru.base_url",
        "services.mineru.uri",
    )
    if mineru_base:
        mineru: dict[str, Any] = {"base_url": mineru_base}
        api_key = _cfg_str(
            "index.parsers.mineru.api_key",
            "CLOUD_DOG__INDEX__PARSERS__MINERU__API_KEY",
            "MINERU_API_KEY",
            "services.mineru.api_key",
        )
        if api_key:
            mineru["api_key"] = api_key
        mineru["timeout_seconds"] = _cfg_float(
            120.0, "index.parsers.mineru.timeout_seconds", "MINERU_TIMEOUT_SECONDS"
        )
        mineru["request_retries"] = _cfg_int(
            3, "index.parsers.mineru.request_retries", "MINERU_REQUEST_RETRIES"
        )
        services["mineru"] = mineru

    marker_base = _cfg_str(
        "index.parsers.marker_mcp.base_url",
        "CLOUD_DOG__INDEX__PARSERS__MARKER_MCP__BASE_URL",
        "MARKER_MCP_BASE_URL",
        "services.marker_mcp.base_url",
    )
    if marker_base:
        marker: dict[str, Any] = {"base_url": marker_base}
        auth_token = _cfg_str(
            "index.parsers.marker_mcp.auth_token",
            "CLOUD_DOG__INDEX__PARSERS__MARKER_MCP__AUTH_TOKEN",
            "MARKER_MCP_AUTH_TOKEN",
        )
        if auth_token:
            marker["auth_token"] = auth_token
        services["marker_mcp"] = marker

    return services


def merge_parser_services(
    caller: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Merge caller-supplied ``parser_services`` over the config defaults.

    Caller values win per key, so an explicit request can still override the
    configured endpoint (e.g. a test pointing at a local MinerU). The operation
    is idempotent, so it is safe to apply at more than one layer.
    """
    merged: dict[str, dict[str, Any]] = {
        name: dict(cfg) for name, cfg in default_parser_services().items()
    }
    for name, cfg in (caller or {}).items():
        if isinstance(cfg, dict):
            base = dict(merged.get(name, {}))
            base.update(cfg)
            merged[name] = base
        else:
            merged[name] = cfg
    return merged

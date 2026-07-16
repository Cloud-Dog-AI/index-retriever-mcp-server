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

"""UNDP HDRO Data API 2.0 extractor.

The API key is resolved through ``cloud_dog_config``/Vault. The Vault ``url``
field is deliberately not trusted unless it names an HDRO host; the canonical
non-secret endpoint is ``https://hdrdata.org``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from index_tools.config.loader import runtime_env_files

HDRO_SOURCE_FAMILY = "UNDP HDRO Data API 2.0"
HDRO_CANONICAL_BASE_URL = "https://hdrdata.org"
HDRO_QUERY_PATH = "/api/CompositeIndices/query"
HDRO_ALLOWED_HOSTS = frozenset({"hdrdata.org", "www.hdrdata.org"})
HDRO_SUPPORTED_INDICATORS = ("HDI", "GII")
HDRO_DEFAULTS_YAML = Path(__file__).resolve().parents[3] / "defaults.hdro.yaml"


class HDROConfigError(ValueError):
    """Configuration error for HDRO extraction."""


class HDRORequestError(RuntimeError):
    """Secret-redacted HDRO request failure."""

    def __init__(
        self,
        *,
        endpoint_host: str,
        endpoint_path: str,
        status: int | None,
        response_class: str,
        retryable: bool,
        message: str,
    ) -> None:
        self.endpoint_host = endpoint_host
        self.endpoint_path = endpoint_path
        self.status = status
        self.response_class = response_class
        self.retryable = retryable
        self.message = _redact_secret_text(message)
        super().__init__(
            json.dumps(
                {
                    "endpoint_host": endpoint_host,
                    "endpoint_path": endpoint_path,
                    "status": status,
                    "response_class": response_class,
                    "retryable": retryable,
                    "message": self.message,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe diagnostic envelope."""
        return {
            "endpoint_host": self.endpoint_host,
            "endpoint_path": self.endpoint_path,
            "status": self.status,
            "response_class": self.response_class,
            "retryable": self.retryable,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class HDROConfig:
    """Resolved HDRO endpoint and credential material."""

    base_url: str
    api_key: str
    endpoint_config_source: str
    endpoint_config_defect: str = ""

    @property
    def endpoint_host(self) -> str:
        """Return the selected endpoint host."""
        return _host(self.base_url)


@dataclass(frozen=True, slots=True)
class HDROHTTPResponse:
    """Minimal transport response for testable HTTP fetches."""

    status: int
    body: bytes
    response_class: str = "http"


Transport = Callable[[str, float], HDROHTTPResponse]


def _host(value: str) -> str:
    parsed = urlparse(str(value).strip())
    return (parsed.hostname or "").lower()


def _redact_secret_text(value: str) -> str:
    text = str(value)
    for marker in ("apikey=", "api-key=", "api_key="):
        index = text.lower().find(marker)
        if index >= 0:
            start = index + len(marker)
            end = start
            while end < len(text) and text[end] not in "&,; ":
                end += 1
            text = f"{text[:start]}[REDACTED]{text[end:]}"
    return text


def mask_hdro_secret(value: str) -> str:
    """Return a stable non-secret description of an HDRO credential."""
    if not value:
        return "<missing>"
    return f"<redacted len={len(value)}>"


def is_safe_hdro_base_url(value: str) -> bool:
    """Return True when ``value`` names an approved HDRO endpoint host."""
    return _host(value) in HDRO_ALLOWED_HOSTS


def _select_base_url(raw_url: str) -> tuple[str, str, str]:
    candidate = str(raw_url or "").strip().rstrip("/")
    if not candidate:
        return HDRO_CANONICAL_BASE_URL, "canonical_default", ""
    host = _host(candidate)
    if host in HDRO_ALLOWED_HOSTS:
        return candidate, "configured_hdro_url", ""
    if host.endswith("maptiler.com"):
        return (
            HDRO_CANONICAL_BASE_URL,
            "canonical_default",
            "Vault dev.external.HDRO.url resolves to maptiler.com and is not used as HDRO",
        )
    raise HDROConfigError(f"Unsafe HDRO endpoint host configured: {host or '<empty>'}")


def _extract_hdro_block(config_data: dict[str, Any]) -> dict[str, Any]:
    external = config_data.get("external", {})
    if not isinstance(external, Mapping):
        return {}
    for key in ("HDRO", "hdro"):
        block = external.get(key)
        if isinstance(block, Mapping):
            return dict(block)
    return {}


def load_hdro_config(config_data: dict[str, Any] | None = None) -> HDROConfig:
    """Resolve HDRO config through the platform config loader."""
    if config_data is None:
        from cloud_dog_config import load_config  # type: ignore

        compiled = load_config(
            env_files=runtime_env_files(),
            defaults_yaml=str(HDRO_DEFAULTS_YAML),
            unresolved_policy="strict",
            vault_enabled=True,
        )
        config_data = dict(compiled.data)

    block = _extract_hdro_block(config_data)
    api_key = str(block.get("api-key") or block.get("api_key") or "").strip()
    if not api_key:
        raise HDROConfigError("Missing required HDRO API key at dev.external.HDRO.api-key")
    base_url, source, defect = _select_base_url(str(block.get("url", "")))
    return HDROConfig(
        base_url=base_url,
        api_key=api_key,
        endpoint_config_source=source,
        endpoint_config_defect=defect,
    )


def build_hdro_query_url(
    config: HDROConfig,
    *,
    country_or_aggregation: str,
    year: int | str,
) -> str:
    """Build the HDRO query URL. The returned value contains the secret."""
    params = {
        "apikey": config.api_key,
        "countryOrAggregation": str(country_or_aggregation).strip(),
        "year": str(year).strip(),
    }
    return f"{config.base_url.rstrip('/')}{HDRO_QUERY_PATH}?{urlencode(params)}"


def build_redacted_hdro_query_url(
    config: HDROConfig,
    *,
    country_or_aggregation: str,
    year: int | str,
) -> str:
    """Build a secret-safe diagnostic URL."""
    params = {
        "apikey": "<redacted>",
        "countryOrAggregation": str(country_or_aggregation).strip(),
        "year": str(year).strip(),
    }
    return f"{config.base_url.rstrip('/')}{HDRO_QUERY_PATH}?{urlencode(params)}"


def _urllib_transport(url: str, timeout_seconds: float) -> HDROHTTPResponse:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return HDROHTTPResponse(
                status=int(getattr(response, "status", 0) or 0),
                body=response.read(),
                response_class="json_http",
            )
    except HTTPError as exc:
        return HDROHTTPResponse(
            status=int(exc.code),
            body=exc.read(),
            response_class="http_error",
        )
    except URLError as exc:
        raise HDRORequestError(
            endpoint_host=_host(url),
            endpoint_path=HDRO_QUERY_PATH,
            status=None,
            response_class=type(exc).__name__,
            retryable=True,
            message=str(exc),
        ) from exc


def _normalise_indicator_tokens(indicators: list[str] | tuple[str, ...] | None) -> set[str]:
    values = indicators or list(HDRO_SUPPORTED_INDICATORS)
    return {str(item).strip().upper() for item in values if str(item).strip()}


def _record_matches_indicator(record: dict[str, Any], wanted: set[str]) -> bool:
    index_text = str(record.get("index", "")).upper()
    indicator_text = str(record.get("indicator", "")).upper()
    for token in wanted:
        if index_text.startswith(f"{token} ") or index_text.startswith(f"{token}-"):
            return True
        if indicator_text.startswith(f"{token} ") or indicator_text.startswith(f"{token}-"):
            return True
    return False


def parse_hdro_records(
    payload: Any,
    *,
    indicators: list[str] | tuple[str, ...] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Parse and filter HDRO response rows."""
    if not isinstance(payload, list):
        raise HDRORequestError(
            endpoint_host="hdrdata.org",
            endpoint_path=HDRO_QUERY_PATH,
            status=200,
            response_class=type(payload).__name__,
            retryable=False,
            message="HDRO response JSON was not a list",
        )
    wanted = _normalise_indicator_tokens(indicators)
    output: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if wanted and not _record_matches_indicator(item, wanted):
            continue
        output.append(
            {
                "country": str(item.get("country", "")),
                "index": str(item.get("index", "")),
                "indicator": str(item.get("indicator", "")),
                "value": str(item.get("value", "")),
                "year": str(item.get("year", "")),
                "dimension": str(item.get("dimension", "")),
            }
        )
        if len(output) >= limit:
            break
    return output


def extract_hdro(
    *,
    country_or_aggregation: str = "AFG",
    year: int | str = 2022,
    indicators: list[str] | tuple[str, ...] | None = None,
    limit: int = 20,
    config_data: dict[str, Any] | None = None,
    transport: Transport | None = None,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    """Fetch and parse HDRO index records."""
    config = load_hdro_config(config_data=config_data)
    endpoint_host = config.endpoint_host
    if endpoint_host not in HDRO_ALLOWED_HOSTS:
        raise HDROConfigError(f"Unsafe HDRO endpoint host selected: {endpoint_host}")

    url = build_hdro_query_url(
        config,
        country_or_aggregation=country_or_aggregation,
        year=year,
    )
    response = (transport or _urllib_transport)(url, timeout_seconds)
    if response.status != 200:
        raise HDRORequestError(
            endpoint_host=endpoint_host,
            endpoint_path=HDRO_QUERY_PATH,
            status=response.status,
            response_class=response.response_class,
            retryable=response.status in {429, 500, 502, 503, 504},
            message=response.body[:300].decode("utf-8", errors="replace"),
        )
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HDRORequestError(
            endpoint_host=endpoint_host,
            endpoint_path=HDRO_QUERY_PATH,
            status=response.status,
            response_class="invalid_json",
            retryable=False,
            message=str(exc),
        ) from exc
    records = parse_hdro_records(payload, indicators=indicators, limit=limit)
    return {
        "source_family": HDRO_SOURCE_FAMILY,
        "canonical_base_url": HDRO_CANONICAL_BASE_URL,
        "base_url": config.base_url,
        "endpoint_host": endpoint_host,
        "endpoint_path": HDRO_QUERY_PATH,
        "redacted_request_url": build_redacted_hdro_query_url(
            config,
            country_or_aggregation=country_or_aggregation,
            year=year,
        ),
        "endpoint_config_source": config.endpoint_config_source,
        "endpoint_config_defect": config.endpoint_config_defect,
        "country_or_aggregation": str(country_or_aggregation),
        "year": str(year),
        "supported_indicators": list(HDRO_SUPPORTED_INDICATORS),
        "requested_indicators": sorted(_normalise_indicator_tokens(indicators)),
        "records": records,
        "record_count": len(records),
        "raw_record_count": len(payload),
    }

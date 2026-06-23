# @pytest.mark.UT
# @pytest.mark.internal
# @pytest.mark.req("FR-009")
# PS-REQ-TEST-TRACE markers are declared in pytestmark below.

# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""W28D-440E5: UNDP HDRO extractor unit coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from index_server.mcp_server import execute_tool
from index_tools.queue.models import JobStatus
from index_tools.sources.hdro import (
    HDRO_CANONICAL_BASE_URL,
    HDRO_QUERY_PATH,
    HDROConfig,
    HDROConfigError,
    HDROHTTPResponse,
    HDRORequestError,
    build_hdro_query_url,
    build_redacted_hdro_query_url,
    extract_hdro,
    load_hdro_config,
    parse_hdro_records,
)
from index_tools.tools.service import IndexService


pytestmark = [pytest.mark.UT, pytest.mark.internal, pytest.mark.req("FR-009")]


def _sample_payload() -> list[dict[str, str]]:
    return [
        {
            "country": "AFG - Afghanistan",
            "index": "HDI - Human Development Index",
            "indicator": "hdi - Human Development Index (value)",
            "value": "0.462",
            "year": "2022",
            "dimension": "",
        },
        {
            "country": "AFG - Afghanistan",
            "index": "GII - Gender Inequality Index",
            "indicator": "gii - Gender Inequality Index (value)",
            "value": "0.665",
            "year": "2022",
            "dimension": "",
        },
        {
            "country": "AFG - Afghanistan",
            "index": "OTHER - Additional Indicators",
            "indicator": "pop_total - Total population",
            "value": "40578842",
            "year": "2022",
            "dimension": "",
        },
    ]


def test_hdro_config_uses_canonical_endpoint_when_vault_url_is_maptiler() -> None:
    config = load_hdro_config(
        {
            "external": {
                "HDRO": {
                    "url": "https://api.maptiler.com/maps",
                    "api-key": "x" * 36,
                }
            }
        }
    )

    assert config.base_url == HDRO_CANONICAL_BASE_URL
    assert config.endpoint_host == "hdrdata.org"
    assert "maptiler.com" in config.endpoint_config_defect


def test_hdro_config_rejects_unknown_non_hdro_endpoint() -> None:
    with pytest.raises(HDROConfigError) as excinfo:
        load_hdro_config(
            {
                "external": {
                    "HDRO": {
                        "url": "https://example.invalid",
                        "api-key": "x" * 36,
                    }
                }
            }
        )

    assert "example.invalid" in str(excinfo.value)


def test_hdro_missing_key_fails_closed_without_network_call() -> None:
    called = False

    def _transport(url: str, timeout_seconds: float) -> HDROHTTPResponse:
        nonlocal called
        called = True
        return HDROHTTPResponse(status=200, body=b"[]")

    with pytest.raises(HDROConfigError):
        extract_hdro(
            config_data={"external": {"HDRO": {"url": "https://hdrdata.org"}}},
            transport=_transport,
        )

    assert called is False


def test_hdro_request_construction_and_redaction() -> None:
    config = HDROConfig(
        base_url="https://hdrdata.org",
        api_key="secret-value-123",
        endpoint_config_source="canonical_default",
    )

    raw_url = build_hdro_query_url(config, country_or_aggregation="AFG", year=2022)
    redacted_url = build_redacted_hdro_query_url(config, country_or_aggregation="AFG", year=2022)

    assert raw_url.startswith("https://hdrdata.org/api/CompositeIndices/query?")
    assert "apikey=secret-value-123" in raw_url
    assert "countryOrAggregation=AFG" in raw_url
    assert "apikey=%3Credacted%3E" in redacted_url
    assert "secret-value-123" not in redacted_url


def test_hdro_response_parsing_filters_hdi_and_gii() -> None:
    records = parse_hdro_records(_sample_payload(), indicators=["HDI", "GII"], limit=10)

    assert len(records) == 2
    assert records[0]["indicator"].startswith("hdi -")
    assert records[1]["indicator"].startswith("gii -")
    assert {row["year"] for row in records} == {"2022"}


def test_hdro_request_errors_do_not_expose_secret_values() -> None:
    secret = "secret-value-123"

    def _transport(url: str, timeout_seconds: float) -> HDROHTTPResponse:
        assert secret in url
        return HDROHTTPResponse(
            status=500,
            body=f"upstream failed for apikey={secret}".encode(),
            response_class="http_error",
        )

    with pytest.raises(HDRORequestError) as excinfo:
        extract_hdro(
            config_data={"external": {"HDRO": {"url": "https://hdrdata.org", "api-key": secret}}},
            transport=_transport,
        )

    text = str(excinfo.value)
    assert secret not in text
    assert "[REDACTED]" in text
    assert "hdrdata.org" in text
    assert HDRO_QUERY_PATH in text
    assert '"retryable": true' in text


def test_hdro_extract_returns_metadata_and_country_values() -> None:
    def _transport(url: str, timeout_seconds: float) -> HDROHTTPResponse:
        assert "apikey=secret-value-123" in url
        return HDROHTTPResponse(
            status=200,
            body=__import__("json").dumps(_sample_payload()).encode(),
            response_class="json_http",
        )

    result = extract_hdro(
        config_data={
            "external": {
                "HDRO": {
                    "url": "https://api.maptiler.com/maps",
                    "api-key": "secret-value-123",
                }
            }
        },
        transport=_transport,
    )

    assert result["source_family"] == "UNDP HDRO Data API 2.0"
    assert result["endpoint_host"] == "hdrdata.org"
    assert result["record_count"] == 2
    assert result["records"][0]["country"] == "AFG - Afghanistan"
    assert result["records"][0]["value"]
    assert "secret-value-123" not in result["redacted_request_url"]


@pytest.fixture()
def service(tmp_path: Path) -> IndexService:
    svc = IndexService(audit_path=str(tmp_path / "audit.jsonl"))
    try:
        yield svc
    finally:
        svc.close()


def test_hdro_extract_invokes_through_mcp_service_surface(monkeypatch: pytest.MonkeyPatch, service: IndexService) -> None:
    from index_tools.sources import hdro

    monkeypatch.setattr(
        hdro,
        "load_hdro_config",
        lambda config_data=None: HDROConfig(
            base_url="https://hdrdata.org",
            api_key="secret-value-123",
            endpoint_config_source="canonical_default",
        ),
    )

    def _transport(url: str, timeout_seconds: float) -> HDROHTTPResponse:
        return HDROHTTPResponse(
            status=200,
            body=__import__("json").dumps(_sample_payload()).encode(),
            response_class="json_http",
        )

    monkeypatch.setattr(hdro, "_urllib_transport", _transport)

    result = execute_tool(
        service,
        "hdro_extract",
        {"country_or_aggregation": "AFG", "year": 2022, "actor": "admin"},
        identity_roles={"admin"},
    )

    assert result["endpoint_host"] == "hdrdata.org"
    assert result["record_count"] == 2


def test_w28d440e1_compact_source_hunt_regression_still_succeeds(service: IndexService) -> None:
    text = (
        "# Transparent Borders DEMO-027 Compact Source Hunt Extract\n\n"
        "- WHO Global Health Observatory OData API\n"
        "- UN Statistics Division SDG API\n"
        "- Eurostat Dissemination Statistics API\n"
        "- World Bank Indicators API\n"
        "- IMF DataMapper API\n"
    )
    job_id = service.ingest_text(
        profile="default",
        collection="w28d440e4-compact-regression",
        text=text,
        source="file-mcp:demo27-transparent-borders-report-generation/captures/compact-index-extract.md",
        actor="test",
    )
    job = service.queue.get(job_id)
    assert job.status == JobStatus.succeeded

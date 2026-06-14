# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""W28D-440E5 live UNDP HDRO integration test."""

from __future__ import annotations

import pytest

from index_tools.sources.hdro import extract_hdro


def test_hdro_live_vault_key_returns_hdi_gii_country_values() -> None:
    result = extract_hdro(country_or_aggregation="AFG", year=2022, indicators=["HDI", "GII"], limit=10)

    assert result["source_family"] == "UNDP HDRO Data API 2.0"
    assert result["endpoint_host"] == "hdrdata.org"
    assert result["endpoint_path"] == "/api/CompositeIndices/query"
    assert result["record_count"] >= 2
    assert result["raw_record_count"] >= result["record_count"]
    assert "HDI" in result["supported_indicators"]
    assert "GII" in result["supported_indicators"]
    assert all(row["country"].startswith("AFG -") for row in result["records"])
    assert any(row["indicator"].lower().startswith("hdi -") for row in result["records"])
    assert any(row["indicator"].lower().startswith("gii -") for row in result["records"])
    assert "apikey" in result["redacted_request_url"]
    assert "<redacted>" not in result["redacted_request_url"]
    assert "%3Credacted%3E" in result["redacted_request_url"]

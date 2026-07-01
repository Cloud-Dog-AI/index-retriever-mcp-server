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

from typing import Any

import pytest

from index_tools.outbound.a2a_client import OutboundA2AClient
from index_tools.outbound.credentials import OutboundServiceResolver
from index_tools.outbound.discovery import ServiceDiscoveryCache
from index_tools.outbound.mcp_client import OutboundMCPClient
from index_tools.pipeline.enrich import (
    apply_enrich_step,
    enrich_steps_from_metadata,
    parse_enrich_spec,
)

pytestmark = [pytest.mark.UT, pytest.mark.mcp, pytest.mark.req("FR-002")]


class _AuditSink:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log_external_call(self, **kwargs: Any) -> None:
        self.events.append(dict(kwargs))


class _NoCacheDiscovery(ServiceDiscoveryCache):
    def __init__(self) -> None:
        pass

    async def get_or_fetch(self, namespace: str, service_name: str, fetcher: Any) -> Any:
        _ = namespace, service_name
        return await fetcher()


def _resolver() -> OutboundServiceResolver:
    values = {
        "outbound.services.search-mcp.uri": "https://search.example",
        "outbound.services.search-mcp.credential_config_key": "dev.services.searchmcp0.api_key",
        "dev.services.searchmcp0.api_key": "unit-key",
    }
    return OutboundServiceResolver(lambda key: values.get(key))


def test_parse_enrich_spec_and_resolve_arguments() -> None:
    step = parse_enrich_spec("search-mcp.enrich(query=$doc.title, depth=quick)")

    assert step.service == "search-mcp"
    assert step.tool == "enrich"
    assert step.arguments == {"query": "$doc.title", "depth": "quick"}


@pytest.mark.asyncio
async def test_apply_enrich_step_merges_related_content_and_quality() -> None:
    class Client:
        async def invoke_tool(
            self,
            tool_name: str,
            arguments: dict[str, Any],
            *,
            correlation_id: str | None = None,
        ) -> dict[str, Any]:
            assert tool_name == "enrich"
            assert arguments == {"query": "Alpha", "depth": "quick"}
            assert correlation_id == "corr-1"
            return {
                "result": {
                    "related_content": [{"title": "Related"}],
                    "quality_classifications": [{"label": "authoritative"}],
                }
            }

    document = {"metadata": {"title": "Alpha"}}
    step = parse_enrich_spec("search-mcp.enrich(query=$doc.title, depth=quick)")

    enriched = await apply_enrich_step(document, step, Client(), correlation_id="corr-1")

    assert enriched["metadata"]["related_content"] == [{"title": "Related"}]
    assert enriched["metadata"]["quality_classifications"] == [{"label": "authoritative"}]
    assert "search-mcp.enrich" in enriched["metadata"]["enrichment"]


def test_source_metadata_builds_enrich_steps() -> None:
    steps = enrich_steps_from_metadata(
        {
            "pipeline": [
                {"enrich": "search-mcp.enrich(query=$doc.title, depth=quick)", "transport": "a2a"},
            ]
        }
    )

    assert len(steps) == 1
    assert steps[0].transport == "a2a"
    assert steps[0].service == "search-mcp"


@pytest.mark.asyncio
async def test_mcp_client_uses_platform_transport_and_propagates_headers() -> None:
    audit = _AuditSink()
    calls: list[tuple[str, dict[str, Any] | None]] = []
    configs: list[Any] = []

    class Transport:
        def __init__(self, cfg: Any) -> None:
            configs.append(cfg)

        async def connect(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
            _ = method, params

        async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            calls.append((method, params))
            if method == "tools/list":
                return {"tools": [{"name": "enrich"}]}
            return {"result": {"ok": True}}

    client = OutboundMCPClient(
        "search-mcp",
        resolver=_resolver(),
        discovery=_NoCacheDiscovery(),
        audit_logger=audit,  # type: ignore[arg-type]
        transport_factory=Transport,
    )

    result = await client.invoke_tool("enrich", {"query": "Alpha"}, correlation_id="corr-1")

    assert result == {"result": {"ok": True}}
    assert [method for method, _ in calls] == ["tools/list", "tools/call"]
    assert configs[-1].extra_headers["X-Correlation-Id"] == "corr-1"
    assert configs[-1].extra_headers["X-API-Key"] == "unit-key"
    assert audit.events[-1]["action"] == "tools/call:enrich"


@pytest.mark.asyncio
async def test_a2a_client_discovers_agent_card_and_invokes_skill() -> None:
    audit = _AuditSink()
    requests: list[tuple[str, str, dict[str, str], dict[str, Any] | None]] = []

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.status_code = 200
            self._payload = payload

        def json(self) -> dict[str, Any]:
            return self._payload

    class Client:
        async def get(self, path: str, *, headers: dict[str, str]) -> Response:
            requests.append(("GET", path, headers, None))
            return Response({"skills": [{"id": "enrich", "name": "Enrich"}]})

        async def post(self, path: str, *, json: dict[str, Any], headers: dict[str, str]) -> Response:
            requests.append(("POST", path, headers, json))
            return Response({"status": "completed", "result": {"ok": True}})

        async def aclose(self) -> None:
            pass

    client = OutboundA2AClient(
        "search-mcp",
        resolver=_resolver(),
        discovery=_NoCacheDiscovery(),
        audit_logger=audit,  # type: ignore[arg-type]
        client_factory=lambda base_url, timeout: Client(),
    )

    skills = await client.list_skills(correlation_id="corr-2")
    result = await client.invoke_tool("enrich", {"query": "Alpha"}, correlation_id="corr-2")

    assert skills == [{"id": "enrich", "name": "Enrich", "description": ""}]
    assert result["status"] == "completed"
    assert requests[0][2]["X-Correlation-Id"] == "corr-2"
    assert requests[1][2]["X-API-Key"] == "unit-key"
    assert requests[1][3]["skill_id"] == "enrich"
    assert audit.events[-1]["action"] == "a2a.task:enrich"

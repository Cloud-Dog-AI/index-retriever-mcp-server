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

"""Outbound PS-72 A2A client for peer service skills."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from cloud_dog_api_kit.clients import ClientTimeout, create_http_client
from cloud_dog_logging import get_correlation_id, get_logger

from index_tools.audit.logger import AuditLogger
from index_tools.outbound.credentials import OutboundServiceConfig, OutboundServiceResolver
from index_tools.outbound.discovery import ServiceDiscoveryCache, extract_agent_skills
from index_tools.outbound.mcp_client import OutboundCircuitBreaker

LOGGER = get_logger(__name__)

HttpClientFactory = Callable[[str, float], Any]


class OutboundA2AClient:
    """Generic A2A task and discovery client for Cloud-Dog peer services."""

    def __init__(
        self,
        service_name: str,
        *,
        resolver: OutboundServiceResolver | None = None,
        discovery: ServiceDiscoveryCache | None = None,
        audit_logger: AuditLogger | None = None,
        circuit_breaker: OutboundCircuitBreaker | None = None,
        client_factory: HttpClientFactory | None = None,
    ) -> None:
        """Initialise without retaining peer credentials."""
        self.service_name = service_name
        self._resolver = resolver or OutboundServiceResolver()
        self._discovery = discovery or ServiceDiscoveryCache()
        self._audit_logger = audit_logger
        self._breaker = circuit_breaker or OutboundCircuitBreaker()
        self._client_factory = client_factory or _default_client

    async def discover_agent_card(self, *, correlation_id: str | None = None) -> dict[str, Any]:
        """Fetch and cache the peer A2A agent card."""
        corr = self._correlation(correlation_id)

        async def _fetch() -> dict[str, Any]:
            payload = await self._request(
                verb="GET",
                path="/.well-known/agent.json",
                body=None,
                action="agent_card",
                correlation_id=corr,
                audit_parameters={},
            )
            return payload if isinstance(payload, dict) else {}

        return await self._discovery.get_or_fetch("a2a-agent-card", self.service_name, _fetch)

    async def list_skills(self, *, correlation_id: str | None = None) -> list[dict[str, Any]]:
        """Return the peer skill list from its PS-72 agent card."""
        return extract_agent_skills(await self.discover_agent_card(correlation_id=correlation_id))

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Compatibility alias used by the ingest enrich pipeline."""
        return await self.submit_task(tool_name, arguments, correlation_id=correlation_id)

    async def submit_task(
        self,
        skill_id: str,
        arguments: dict[str, Any],
        *,
        correlation_id: str | None = None,
        task_id: str = "",
    ) -> dict[str, Any]:
        """Submit an A2A task to a peer skill."""
        corr = self._correlation(correlation_id)
        payload = {
            "id": task_id or corr,
            "skill_id": skill_id,
            "input": {"arguments": dict(arguments)},
            "correlation_id": corr,
        }
        return await self._request(
            verb="POST",
            path=self._resolver.resolve(self.service_name, transport="a2a").tasks_path,
            body=payload,
            action=f"a2a.task:{skill_id}",
            correlation_id=corr,
            audit_parameters={"skill_id": skill_id, "arguments": dict(arguments)},
        )

    async def task_status(self, task_id: str, *, correlation_id: str | None = None) -> dict[str, Any]:
        """Poll a peer A2A task status endpoint."""
        corr = self._correlation(correlation_id)
        return await self._request(
            verb="GET",
            path=f"/a2a/tasks/{task_id}",
            body=None,
            action="a2a.task_status",
            correlation_id=corr,
            audit_parameters={"task_id": task_id},
        )

    async def _request(
        self,
        *,
        verb: str,
        path: str,
        body: dict[str, Any] | None,
        action: str,
        correlation_id: str,
        audit_parameters: dict[str, Any],
    ) -> dict[str, Any]:
        config = self._resolver.resolve(self.service_name, transport="a2a")
        if not config.resolved_a2a_url:
            raise ValueError(f"Outbound A2A service is not configured: {self.service_name}")
        start = time.monotonic()
        outcome = "success"
        error = ""
        status_code = 0
        try:
            self._breaker.before_call()
            client = self._client_factory(config.resolved_a2a_url, config.timeout_seconds)
            try:
                headers = self._resolver.headers(config, correlation_id=correlation_id)
                if verb == "GET":
                    response = await client.get(path, headers=headers)
                else:
                    response = await client.post(path, json=body or {}, headers=headers)
                status_code = int(getattr(response, "status_code", 0) or 0)
                payload = response.json()
                if status_code >= 400:
                    raise RuntimeError(f"A2A task request failed with HTTP {status_code}: {str(payload)[:400]}")
                self._breaker.on_success()
                return payload if isinstance(payload, dict) else {"value": payload}
            finally:
                close = getattr(client, "aclose", None)
                if callable(close):
                    await close()
        except Exception as exc:
            outcome = "failure"
            error = str(exc)
            self._breaker.on_failure()
            raise
        finally:
            self._emit_external_call(
                config=config,
                action=action,
                outcome=outcome,
                correlation_id=correlation_id,
                duration_ms=int((time.monotonic() - start) * 1000),
                status_code=status_code,
                parameters=audit_parameters,
                error=error,
            )

    def _emit_external_call(
        self,
        *,
        config: OutboundServiceConfig,
        action: str,
        outcome: str,
        correlation_id: str,
        duration_ms: int,
        status_code: int,
        parameters: dict[str, Any],
        error: str,
    ) -> None:
        if self._audit_logger is None:
            return
        try:
            details = dict(parameters)
            details["status_code"] = status_code
            self._audit_logger.log_external_call(
                actor="index-retriever-mcp-server",
                action=action,
                target_service=self.service_name,
                destination_address=config.resolved_a2a_url,
                component="index_tools.outbound.a2a_client",
                outcome=outcome,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                parameters=details,
                error=error,
            )
        except Exception as exc:  # pragma: no cover - defensive audit containment
            LOGGER.warning("outbound_a2a_audit_failed", error=str(exc), peer=self.service_name)

    @staticmethod
    def _correlation(correlation_id: str | None) -> str:
        current = correlation_id or get_correlation_id() or ""
        return str(current or "outbound-index-retriever")


def _default_client(base_url: str, timeout_seconds: float) -> Any:
    return create_http_client(
        base_url=base_url,
        timeout=ClientTimeout(connect=min(5.0, timeout_seconds), read=timeout_seconds, total=timeout_seconds),
        app_id="index-retriever-mcp-server",
    )


__all__ = ["OutboundA2AClient"]

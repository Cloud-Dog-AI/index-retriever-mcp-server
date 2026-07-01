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

"""Outbound MCP client using cloud_dog_api_kit streamable HTTP transport."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cloud_dog_api_kit.mcp.client_sdk import AsyncJobClient
from cloud_dog_api_kit.mcp.client_transport.base import MCPTransport
from cloud_dog_api_kit.mcp.client_transport.streamable_http import StreamableHTTPConfig, StreamableHTTPTransport
from cloud_dog_logging import get_correlation_id, get_logger

from index_tools.audit.logger import AuditLogger
from index_tools.outbound.credentials import OutboundServiceConfig, OutboundServiceResolver
from index_tools.outbound.discovery import ServiceDiscoveryCache

LOGGER = get_logger(__name__)


class OutboundCircuitOpen(RuntimeError):
    """Raised when a peer service circuit is open."""


@dataclass(slots=True)
class OutboundCircuitBreaker:
    """Small circuit breaker for outbound peer calls."""

    failure_threshold: int = 3
    reset_seconds: float = 60.0
    failure_count: int = 0
    opened_at: float = 0.0

    def before_call(self) -> None:
        """Raise when the breaker is open and reset has not elapsed."""
        if not self.opened_at:
            return
        if time.monotonic() - self.opened_at >= self.reset_seconds:
            self.failure_count = 0
            self.opened_at = 0.0
            return
        raise OutboundCircuitOpen("outbound service circuit is open")

    def on_success(self) -> None:
        """Record a successful peer call."""
        self.failure_count = 0
        self.opened_at = 0.0

    def on_failure(self) -> None:
        """Record a failed peer call and open when threshold is reached."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = time.monotonic()


TransportFactory = Callable[[StreamableHTTPConfig], MCPTransport]


class OutboundMCPClient:
    """MCP JSON-RPC outbound client for peer service tools."""

    def __init__(
        self,
        service_name: str,
        *,
        resolver: OutboundServiceResolver | None = None,
        discovery: ServiceDiscoveryCache | None = None,
        audit_logger: AuditLogger | None = None,
        circuit_breaker: OutboundCircuitBreaker | None = None,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        """Initialise the client without storing peer credentials."""
        self.service_name = service_name
        self._resolver = resolver or OutboundServiceResolver()
        self._discovery = discovery or ServiceDiscoveryCache()
        self._audit_logger = audit_logger
        self._breaker = circuit_breaker or OutboundCircuitBreaker()
        self._transport_factory = transport_factory or StreamableHTTPTransport
        self.jobs = AsyncJobClient(call_tool=self.invoke_tool, poll_job=self.poll_job)

    async def discover_tools(self, *, correlation_id: str | None = None) -> list[dict[str, Any]]:
        """Discover MCP tools from the peer service, cached for the discovery TTL."""
        corr = self._correlation(correlation_id)

        async def _fetch() -> list[dict[str, Any]]:
            result = await self._request(
                method="tools/list",
                params=None,
                action="tools/list",
                correlation_id=corr,
                audit_parameters={},
            )
            tools = result.get("tools")
            return list(tools) if isinstance(tools, list) else []

        return await self._discovery.get_or_fetch("mcp-tools", self.service_name, _fetch)

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        correlation_id: str | None = None,
        validate_tool: bool = True,
    ) -> dict[str, Any]:
        """Invoke one MCP tool with correlation propagation and audit."""
        corr = self._correlation(correlation_id or str(arguments.get("correlation_id") or ""))
        if validate_tool:
            tools = await self.discover_tools(correlation_id=corr)
            tool_ids = {str(tool.get("name") or tool.get("id") or "") for tool in tools if isinstance(tool, dict)}
            if tool_ids and tool_name not in tool_ids:
                raise ValueError(f"MCP tool not advertised by {self.service_name}: {tool_name}")
        return await self._request(
            method="tools/call",
            params={"name": tool_name, "arguments": dict(arguments)},
            action=f"tools/call:{tool_name}",
            correlation_id=corr,
            audit_parameters={"tool": tool_name, "arguments": dict(arguments)},
        )

    async def poll_job(self, job_id: str) -> dict[str, Any]:
        """Poll a peer job through the conventional research_status tool."""
        return await self.invoke_tool("research_status", {"job_id": job_id}, validate_tool=False)

    async def _request(
        self,
        *,
        method: str,
        params: dict[str, Any] | None,
        action: str,
        correlation_id: str,
        audit_parameters: dict[str, Any],
    ) -> dict[str, Any]:
        config = self._resolver.resolve(self.service_name, transport="mcp")
        if not config.resolved_mcp_url:
            raise ValueError(f"Outbound MCP service is not configured: {self.service_name}")
        start = time.monotonic()
        outcome = "success"
        error = ""
        try:
            self._breaker.before_call()
            transport = self._transport(config=config, correlation_id=correlation_id)
            await transport.connect()
            try:
                result = await transport.request(method, params=params)
            finally:
                await transport.close()
            self._breaker.on_success()
            return result
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
                parameters=audit_parameters,
                error=error,
            )

    def _transport(self, *, config: OutboundServiceConfig, correlation_id: str) -> MCPTransport:
        headers = self._resolver.headers(config, correlation_id=correlation_id)
        return self._transport_factory(
            StreamableHTTPConfig(
                base_url=config.resolved_mcp_url,
                mcp_path=config.mcp_path,
                accept_header="application/json, text/event-stream",
                sse_accept_header="text/event-stream",
                enable_sse=False,
                timeout_seconds=config.timeout_seconds,
                extra_headers=headers,
            )
        )

    def _emit_external_call(
        self,
        *,
        config: OutboundServiceConfig,
        action: str,
        outcome: str,
        correlation_id: str,
        duration_ms: int,
        parameters: dict[str, Any],
        error: str,
    ) -> None:
        if self._audit_logger is None:
            return
        try:
            self._audit_logger.log_external_call(
                actor="index-retriever-mcp-server",
                action=action,
                target_service=self.service_name,
                destination_address=config.resolved_mcp_url,
                component="index_tools.outbound.mcp_client",
                outcome=outcome,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                parameters=parameters,
                error=error,
            )
        except Exception as exc:  # pragma: no cover - defensive audit containment
            LOGGER.warning("outbound_mcp_audit_failed", error=str(exc), peer=self.service_name)

    @staticmethod
    def _correlation(correlation_id: str | None) -> str:
        current = correlation_id or get_correlation_id() or ""
        return str(current or "outbound-index-retriever")


__all__ = ["OutboundCircuitBreaker", "OutboundCircuitOpen", "OutboundMCPClient"]

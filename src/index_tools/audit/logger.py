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

from pathlib import Path
from typing import Any

from cloud_dog_storage import path_utils
from cloud_dog_logging.audit_logger import AuditLogger as PlatformAuditLogger
from cloud_dog_logging.audit_schema import Actor, AuditEvent, Target
from cloud_dog_logging.correlation import get_correlation_id, set_correlation_id, set_service_name
from cloud_dog_logging.sinks.file_sink import FileSink

try:
    from cloud_dog_logging.correlation import set_environment
except ImportError:  # pragma: no cover - compatibility for older platform wheels
    def set_environment(_value: str) -> None:
        """Fallback no-op when platform correlation context lacks environment support."""


try:
    from cloud_dog_logging.correlation import set_service_instance
except ImportError:  # pragma: no cover - compatibility for older platform wheels
    def set_service_instance(_value: str) -> None:
        """Fallback no-op when platform correlation context lacks service-instance support."""


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
    """Thin adapter over cloud_dog_logging structured audit."""

    def __init__(
        self,
        path: str,
        *,
        server_id: str | None = None,
        service_name: str = "index-retriever-mcp-server",
        environment: str = "dev",
    ) -> None:
        """Initialise the audit sink adapter."""
        resolved_path = path_utils.resolve_path(path)
        path_utils.mkdir(path_utils.parent(resolved_path))
        self.path = Path(resolved_path)
        self.server_id = (server_id or "").strip() or "index-retriever-local"
        self.service_name = service_name
        self.environment = environment.strip() or "dev"
        self._platform = PlatformAuditLogger(
            service_name=self.service_name,
            sink=FileSink(str(self.path)),
        )
        # Bind context immediately so cloud_dog_api_kit AuditMiddleware
        # picks up service/environment on its first request.
        self._bind_context()

    def _bind_context(self) -> None:
        set_service_name(self.service_name)
        set_service_instance(self.server_id)
        set_environment(self.environment)

    @staticmethod
    def _actor(
        actor: str,
        *,
        roles: set[str] | list[str] | tuple[str, ...] | None = None,
        actor_type: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Actor:
        resolved_type = actor_type or ("system" if actor.strip().lower() in {"system", "service"} else "user")
        role_list = sorted(str(item) for item in roles) if roles else None
        actor_kwargs: dict[str, Any] = {
            "type": resolved_type,
            "id": actor or "unknown",
            "roles": role_list,
            "ip": ip,
            "user_agent": user_agent,
        }
        try:
            return Actor(**actor_kwargs)
        except TypeError:
            # Older cloud_dog_logging wheels do not expose ip/user_agent on Actor.
            actor_kwargs.pop("ip", None)
            actor_kwargs.pop("user_agent", None)
            return Actor(**actor_kwargs)

    @staticmethod
    def _target(target_type: str, target_id: str, *, target_name: str | None = None) -> Target:
        target_kwargs: dict[str, Any] = {"type": target_type, "id": target_id, "name": target_name}
        try:
            return Target(**target_kwargs)
        except TypeError:
            target_kwargs.pop("name", None)
            return Target(**target_kwargs)

    def write_event(self, event: AuditEvent) -> None:
        """Emit a platform audit event via the configured platform sink."""
        self._bind_context()
        self._platform.emit(event)

    def log_ingest(
        self,
        *,
        actor: str,
        profile: str,
        collection: str,
        job_id: str,
        source: str,
        metadata: dict[str, Any] | None,
        chunk_count: int,
        document_count: int = 1,
    ) -> None:
        """Write a structured ingest audit event."""
        self.write_event(
            self.build_event(
                event_type="tool.call",
                actor=self._actor(actor),
                action="execute",
                outcome="success",
                target=self._target("tool", "ingest_text", target_name="ingest_text"),
                details={
                    "tool": "ingest_text",
                    "params": {
                        "profile": profile,
                        "collection": collection,
                        "source": source,
                        "metadata": redact_payload(metadata or {}),
                    },
                    "job_id": job_id,
                    "document_count": document_count,
                    "chunk_count": chunk_count,
                    "server_id": self.server_id,
                },
                duration_ms=0,
            )
        )

    def log_admin_action(
        self,
        *,
        actor: str,
        roles: set[str],
        action: str,
        target_type: str,
        target_id: str,
        target_name: str | None = None,
        prior_value: Any | None = None,
        new_value: Any | None = None,
        outcome: str = "success",
        **details: Any,
    ) -> None:
        """Write a privileged admin audit event."""
        self._bind_context()
        actor_obj = self._actor(actor, roles=roles)
        target_obj = self._target(target_type, target_id, target_name=target_name)
        audit_details = {
            "server_id": self.server_id,
            **details,
        }
        if prior_value is not None:
            audit_details["prior_value"] = prior_value
        if new_value is not None:
            audit_details["new_value"] = new_value

        log_privileged = getattr(self._platform, "log_privileged", None)
        if callable(log_privileged):
            log_privileged(
                actor=actor_obj,
                action=action,
                target=target_obj,
                outcome=outcome,
                command_text=f"{target_type}.{action}",
                **audit_details,
            )
            return

        self._platform.log_crud(
            actor=actor_obj,
            action=action,
            target=target_obj,
            outcome=outcome,
            **audit_details,
        )

    def log_security_event(
        self,
        *,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        outcome: str,
        roles: set[str] | None = None,
        actor_type: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        **details: Any,
    ) -> None:
        """Write a security/authentication audit event."""
        self._bind_context()
        self._platform.log_security(
            actor=self._actor(actor, roles=roles, actor_type=actor_type, ip=ip, user_agent=user_agent),
            action=action,
            target=self._target(target_type, target_id),
            outcome=outcome,
            server_id=self.server_id,
            **details,
        )

    def log_external_call(
        self,
        *,
        actor: str,
        action: str,
        target_service: str,
        destination_address: str,
        component: str,
        outcome: str,
        correlation_id: str,
        duration_ms: int,
        parameters: dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        """Write a PS-AUDIT-LOG external.call audit event."""
        self._bind_context()
        previous_correlation = get_correlation_id()
        try:
            if correlation_id:
                set_correlation_id(correlation_id)
            details = {
                "server_id": self.server_id,
                "destination_address": destination_address,
                "parameters": redact_payload(parameters or {}),
            }
            if error:
                details["error"] = {"message": str(error)[:500]}
            try:
                event = AuditEvent(
                    event_type="external.call",
                    actor=self._actor(actor, roles=["service"], actor_type="service"),
                    action=action,
                    outcome=outcome,
                    correlation_id=correlation_id or get_correlation_id(),
                    service=self.service_name,
                    service_instance=self.server_id,
                    environment=self.environment,
                    component=component,
                    target=self._target("service", target_service, target_name=target_service),
                    destination_address=destination_address,
                    details=details,
                    duration_ms=duration_ms,
                )
            except TypeError:
                event = self.build_event(
                    event_type="external.call",
                    actor=self._actor(actor, roles=["service"], actor_type="service"),
                    action=action,
                    outcome=outcome,
                    target=self._target("service", target_service, target_name=target_service),
                    details=details,
                    duration_ms=duration_ms,
                )
            self.write_event(event)
        finally:
            set_correlation_id(previous_correlation)

    def build_event(
        self,
        *,
        event_type: str,
        actor: Actor,
        action: str,
        outcome: str,
        target: Target | None = None,
        severity: str = "INFO",
        details: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> AuditEvent:
        """Build a concrete platform audit event for direct emission in tests."""
        self._bind_context()
        correlation_id = get_correlation_id()
        redacted_details = redact_payload(details or {}) if details else None
        try:
            return AuditEvent(
                event_type=event_type,
                actor=actor,
                action=action,
                outcome=outcome,
                correlation_id=correlation_id,
                service=self.service_name,
                service_instance=self.server_id,
                environment=self.environment,
                severity=severity,
                target=target,
                details=redacted_details,
                duration_ms=duration_ms,
            )
        except TypeError:
            return AuditEvent(
                event_type=event_type,
                actor=actor,
                action=action,
                outcome=outcome,
                correlation_id=correlation_id,
                service=self.service_name,
                target=target,
                details=redacted_details,
                duration_ms=duration_ms,
            )

    def get_backend_name(self) -> str:
        """Return the active audit backend identifier."""
        return "cloud_dog_logging"

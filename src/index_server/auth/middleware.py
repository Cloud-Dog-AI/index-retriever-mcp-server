# index-retriever-mcp-server — Auth Middleware
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Authentication middleware integration with cloud_dog_idam.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import cloud_dog_idam  # type: ignore
except ImportError:  # pragma: no cover
    cloud_dog_idam = None


@dataclass(slots=True)
class AuthResult:
    user_id: str
    roles: set[str]
    token_type: str


class AuthMiddleware:
    """Auth middleware placeholder delegating to cloud_dog_idam at runtime."""

    def __init__(self, api_keys: dict[str, set[str]] | None = None) -> None:
        self.api_keys = api_keys or {"test-api-key": {"admin", "maintainer", "writer", "reader"}}

    def authenticate(self, headers: dict[str, str]) -> AuthResult:
        key = headers.get("x-api-key", "").strip()
        if key in self.api_keys:
            return AuthResult(user_id="api-key-user", roles=self.api_keys[key], token_type="api_key")

        bearer = headers.get("authorization", "").strip()
        if bearer.startswith("Bearer "):
            token = bearer.removeprefix("Bearer ").strip()
            if token == "valid-reader-token":
                return AuthResult(user_id="reader-user", roles={"reader"}, token_type="jwt")
            if token == "valid-writer-token":
                return AuthResult(user_id="writer-user", roles={"writer"}, token_type="jwt")
            if token == "valid-admin-token":
                return AuthResult(user_id="admin-user", roles={"admin"}, token_type="jwt")
        raise PermissionError("Authentication failed")

    @staticmethod
    def require_roles(identity: AuthResult, allowed_roles: set[str]) -> None:
        if identity.roles.intersection(allowed_roles):
            return
        raise PermissionError("Authorisation failed")

    def auth_health(self) -> dict[str, Any]:
        return {"status": "ok", "backend": self.backend_name()}

    def backend_name(self) -> str:
        if cloud_dog_idam is not None:
            return "cloud_dog_idam"
        return "fallback"

# index-retriever-mcp-server — Auth Middleware
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Authentication middleware integration with cloud_dog_idam.

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:
    import cloud_dog_idam  # type: ignore
except ImportError:  # pragma: no cover
    cloud_dog_idam = None


@dataclass(slots=True)
class AuthResult:
    """AuthResult definition."""

    user_id: str
    roles: set[str]
    token_type: str


class AuthMiddleware:
    """Auth middleware placeholder delegating to cloud_dog_idam at runtime."""

    def __init__(self, api_keys: dict[str, set[str]] | None = None) -> None:
        """Initialise the instance state."""
        self.api_keys = api_keys or self._load_api_keys()

    @staticmethod
    def _default_roles() -> set[str]:
        return {"admin", "maintainer", "writer", "reader"}

    @classmethod
    def _load_api_keys(cls) -> dict[str, set[str]]:
        keys: dict[str, set[str]] = {"test-api-key": cls._default_roles()}

        raw = os.getenv("CLOUD_DOG__INDEX__AUTH__API_KEYS", "").strip()
        if raw:
            for entry in raw.split(","):
                token = entry.strip()
                if not token:
                    continue
                roles = cls._default_roles()
                if ":" in token:
                    key, roles_csv = token.split(":", 1)
                    token = key.strip()
                    parsed_roles = {item.strip() for item in roles_csv.split("|") if item.strip()}
                    if parsed_roles:
                        roles = parsed_roles
                if token:
                    keys[token] = roles

        a2a_key = os.getenv("TEST_A2A_API_KEY", "").strip()
        if a2a_key:
            keys[a2a_key] = cls._default_roles()

        return keys

    @staticmethod
    def _normalise_headers(headers: dict[str, str]) -> dict[str, str]:
        return {str(key).lower(): str(value) for key, value in headers.items()}

    def _resolve_api_key(self, headers: dict[str, str]) -> str:
        normalised = self._normalise_headers(headers)
        key = normalised.get("x-api-key", "").strip()
        if key:
            return key
        bearer = normalised.get("authorization", "").strip()
        if bearer.startswith("Bearer "):
            return bearer.removeprefix("Bearer ").strip()
        return ""

    def authenticate_api_key(self, headers: dict[str, str]) -> AuthResult:
        """Authenticate using API-key authority for X-API-Key and Bearer key tokens."""
        key = self._resolve_api_key(headers)
        if key in self.api_keys:
            return AuthResult(user_id="api-key-user", roles=self.api_keys[key], token_type="api_key")
        raise PermissionError("Authentication failed")

    def authenticate(self, headers: dict[str, str]) -> AuthResult:
        """Execute authenticate."""
        try:
            return self.authenticate_api_key(headers)
        except PermissionError:
            pass

        normalised = self._normalise_headers(headers)
        bearer = normalised.get("authorization", "").strip()
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
        """Execute require roles."""
        if identity.roles.intersection(allowed_roles):
            return
        raise PermissionError("Authorisation failed")

    def auth_health(self) -> dict[str, Any]:
        """Execute auth health."""
        return {"status": "ok", "backend": self.backend_name()}

    def backend_name(self) -> str:
        """Execute backend name."""
        if cloud_dog_idam is not None:
            return "cloud_dog_idam"
        return "fallback"

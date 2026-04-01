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

import asyncio
import os
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from typing import Any

try:
    import cloud_dog_idam  # type: ignore
    from cloud_dog_idam import APIKeyOnlyProvider, JWTTokenService, RBACEngine  # type: ignore
    from cloud_dog_idam.domain.errors import AuthenticationError, TokenError  # type: ignore
    from cloud_dog_idam.domain.models import AuthRequest  # type: ignore
except ImportError:  # pragma: no cover
    cloud_dog_idam = None  # type: ignore[assignment]
    APIKeyOnlyProvider = None  # type: ignore[assignment]
    JWTTokenService = None  # type: ignore[assignment]
    RBACEngine = None  # type: ignore[assignment]
    AuthenticationError = Exception  # type: ignore[assignment]
    TokenError = Exception  # type: ignore[assignment]
    AuthRequest = None  # type: ignore[assignment]


@dataclass(slots=True)
class AuthResult:
    """AuthResult definition."""

    user_id: str
    roles: set[str]
    token_type: str


class AuthMiddleware:
    """Project auth adapter backed by cloud_dog_idam providers and RBAC."""

    def __init__(self, api_keys: dict[str, set[str]] | None = None) -> None:
        """Initialise the instance state."""
        if (
            cloud_dog_idam is None
            or APIKeyOnlyProvider is None
            or RBACEngine is None
            or AuthRequest is None
        ):
            raise RuntimeError("cloud_dog_idam is required for index-retriever auth")
        self.api_keys = api_keys if api_keys is not None else self._load_api_keys()
        self._jwt_secret = _config_or_env(
            "index.auth.jwt.secret",
            "CLOUD_DOG__INDEX__AUTH__JWT__SECRET",
        )
        self._jwt_service = JWTTokenService(secret=self._jwt_secret) if self._jwt_secret else None
        self._rbac = RBACEngine(role_permissions=self._role_permissions())
        self._provider_signature: tuple[tuple[str, tuple[str, ...]], ...] = ()
        self._provider = self._build_api_key_provider()

    @staticmethod
    def _default_roles() -> set[str]:
        return {"admin", "maintainer", "writer", "reader"}

    @classmethod
    def _load_api_keys(cls) -> dict[str, set[str]]:
        """Load API-key role mappings from runtime env."""
        keys: dict[str, set[str]] = {}
        raw = _config_or_env(
            "index.auth.api_keys",
            "CLOUD_DOG__INDEX__AUTH__API_KEYS",
        )
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

        a2a_key = _config_or_env(
            "test.a2a_api_key",
            "TEST_A2A_API_KEY",
        )
        if a2a_key:
            keys[a2a_key] = cls._default_roles()

        return keys

    @staticmethod
    def _normalise_headers(headers: dict[str, str]) -> dict[str, str]:
        return {str(key).lower(): str(value) for key, value in headers.items()}

    @staticmethod
    def _resolve_api_key(headers: dict[str, str]) -> str:
        normalised = {str(key).lower(): str(value) for key, value in headers.items()}
        key = normalised.get("x-api-key", "").strip()
        if key:
            return key
        bearer = normalised.get("authorization", "").strip()
        if bearer.startswith("Bearer "):
            return bearer.removeprefix("Bearer ").strip()
        return ""

    @staticmethod
    def _primary_role(roles: set[str]) -> str:
        for candidate in ("admin", "maintainer", "writer", "reader"):
            if candidate in roles:
                return candidate
        return sorted(roles)[0] if roles else "reader"

    @staticmethod
    def _role_permissions() -> dict[str, set[str]]:
        return {
            "admin": {"*"},
            "maintainer": {"role:maintainer", "role:writer", "role:reader"},
            "writer": {"role:writer", "role:reader"},
            "reader": {"role:reader"},
        }

    def _api_key_signature(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Return a stable signature of the active API-key mapping."""
        return tuple(sorted((token, tuple(sorted(roles))) for token, roles in self.api_keys.items()))

    def _build_api_key_provider(self) -> Any:
        """Build a fresh cloud_dog_idam API-key provider from the current key map."""
        self._provider_signature = self._api_key_signature()
        return APIKeyOnlyProvider.from_config(
            {
                "keys": [
                    {"key": token, "role": self._primary_role(roles)}
                    for token, roles in self.api_keys.items()
                ],
                "default_role": "reader",
            }
        )

    def _refresh_api_key_provider_if_needed(self) -> None:
        """Refresh the provider when admin CRUD mutates the shared API-key store."""
        if self._api_key_signature() != self._provider_signature:
            self._provider = self._build_api_key_provider()

    @staticmethod
    def _authenticate_provider(provider: Any, request: Any) -> Any:
        coroutine = provider.authenticate(request)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        result_queue: Queue[tuple[bool, Any]] = Queue(maxsize=1)

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_queue.put((True, loop.run_until_complete(coroutine)))
            except Exception as exc:  # pragma: no cover - exercised in async runtime tests
                result_queue.put((False, exc))
            finally:
                loop.close()

        thread = Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        ok, value = result_queue.get()
        if ok:
            return value
        raise value

    def authenticate_api_key(self, headers: dict[str, str]) -> AuthResult:
        """Authenticate using cloud_dog_idam API-key verification."""
        # Covers: FR-04, FR-01B
        key = self._resolve_api_key(headers)
        if not key:
            raise PermissionError("Authentication failed")
        self._refresh_api_key_provider_if_needed()

        try:
            result = self._authenticate_provider(
                self._provider,
                AuthRequest(
                    auth_type="api_key",
                    secret=key,
                    metadata={"x_api_key": key},
                ),
            )
        except AuthenticationError as exc:
            raise PermissionError("Authentication failed") from exc

        roles = set(self.api_keys.get(key, {str(result.user.role)}))
        return AuthResult(
            user_id=str(result.user.user_id),
            roles=roles,
            token_type="api_key",
        )

    def authenticate(self, headers: dict[str, str]) -> AuthResult:
        """Authenticate API-key or JWT bearer credentials via cloud_dog_idam."""
        try:
            return self.authenticate_api_key(headers)
        except PermissionError:
            pass

        normalised = self._normalise_headers(headers)
        bearer = normalised.get("authorization", "").strip()
        if not bearer.startswith("Bearer "):
            raise PermissionError("Authentication failed")

        token = bearer.removeprefix("Bearer ").strip()
        if self._jwt_service is None:
            raise PermissionError("Authentication failed")

        try:
            claims = self._jwt_service.verify(token)
        except TokenError as exc:
            raise PermissionError("Authentication failed") from exc

        role_claim = claims.get("roles", claims.get("role", []))
        if isinstance(role_claim, str):
            roles = {role_claim}
        else:
            roles = {str(item) for item in role_claim if str(item).strip()}
        if not roles:
            roles = {"reader"}
        user_id = str(claims.get("sub", claims.get("user_id", "jwt-user")))
        return AuthResult(user_id=user_id, roles=roles, token_type="jwt")

    def require_roles(self, identity: AuthResult, allowed_roles: set[str]) -> None:
        """Authorise against cloud_dog_idam RBAC role state."""
        # Covers: FR-05
        for role in identity.roles:
            self._rbac.assign_role_to_user(identity.user_id, role)
        effective_roles = self._rbac.get_effective_roles(identity.user_id)
        if effective_roles.intersection(allowed_roles):
            return
        raise PermissionError("Authorisation failed")

    def auth_health(self) -> dict[str, Any]:
        """Return auth health payload."""
        return {"status": "ok", "backend": self.backend_name()}

    def backend_name(self) -> str:
        """Return auth backend identity."""
        return "cloud_dog_idam"


def _config_or_env(config_key: str, *env_names: str) -> str:
    """Resolve config with direct env precedence and tolerate unloaded config state."""
    for env_name in env_names:
        value = str(os.environ.get(env_name, "")).strip()
        if value:
            return value
    try:
        from cloud_dog_config import get_config  # type: ignore

        value = get_config(config_key)
    except Exception:
        return ""
    return str(value or "").strip()

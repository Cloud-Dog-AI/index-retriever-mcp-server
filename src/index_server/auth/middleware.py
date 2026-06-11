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
from datetime import datetime, timezone
from queue import Queue
from typing import Any
from uuid import uuid4

try:
    import cloud_dog_idam  # type: ignore
    from cloud_dog_idam import APIKeyManager, JWTTokenService, RBACEngine  # type: ignore
    from cloud_dog_idam.api_keys.hashing import hash_api_key  # type: ignore
    from cloud_dog_idam.domain.enums import UserStatus as IDAMUserStatus  # type: ignore
    from cloud_dog_idam.domain.errors import AuthenticationError, TokenError  # type: ignore
    from cloud_dog_idam.domain.models import ApiKey as IDAMApiKey  # type: ignore
    from cloud_dog_idam.domain.models import AuthRequest, User as IDAMUser  # type: ignore
    from cloud_dog_idam.providers.api_key import APIKeyProvider  # type: ignore
except ImportError:  # pragma: no cover — cloud_dog_idam is a required dependency
    raise ImportError("cloud_dog_idam is required — install via: pip install cloud-dog-idam>=0.2.0")


@dataclass(slots=True)
class AuthResult:
    """AuthResult definition."""

    user_id: str
    roles: set[str]
    permissions: set[str]
    token_type: str


INDEX_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "user": {"collection.read", "collection.write", "source.configure"},
    "viewer": {"collection.read"},
}

_LEGACY_ROLE_ALIASES = {
    "maintainer": "user",
    "writer": "user",
    "read-write": "user",
    "reader": "viewer",
    "read-only": "viewer",
    "owner": "admin",
}


def _canonical_role(raw_role: str) -> str:
    role = str(raw_role or "").strip().lower()
    return _LEGACY_ROLE_ALIASES.get(role, role or "viewer")


def flat_roles_for(roles: set[str]) -> set[str]:
    """Project internal RBAC roles back to the Thread-a flat login roles."""
    canonical_roles = {_canonical_role(role) for role in roles}
    if "admin" in canonical_roles:
        return set(("admin",))
    if "user" in canonical_roles:
        return {"read-write"}
    if "viewer" in canonical_roles:
        return {"read-only"}
    return set()


class AuthMiddleware:
    """Project auth adapter backed by cloud_dog_idam providers and RBAC."""

    def __init__(self, api_keys: dict[str, set[str]] | None = None) -> None:
        """Initialise the instance state."""
        if (
            cloud_dog_idam is None
            or APIKeyManager is None
            or APIKeyProvider is None
            or RBACEngine is None
            or AuthRequest is None
        ):
            raise RuntimeError("cloud_dog_idam is required for index-retriever auth")
        self._jwt_secret = _config_or_env(
            "index.auth.jwt.secret",
            "CLOUD_DOG__INDEX__AUTH__JWT__SECRET",
        )
        self._jwt_service = JWTTokenService(secret=self._jwt_secret) if self._jwt_secret else None
        self._rbac = RBACEngine(role_permissions=INDEX_ROLE_PERMISSIONS)
        self._users: dict[str, IDAMUser] = {}
        self._api_key_manager = APIKeyManager(default_prefix="cd_")
        self._provider = APIKeyProvider(self._api_key_manager, self._users.get)
        self._seed_configured_keys(api_keys)

    @staticmethod
    def _default_roles() -> set[str]:
        return set()

    @classmethod
    def _configured_key_roles(cls) -> list[tuple[str, set[str]]]:
        """Resolve configured bootstrap keys for IDAM seeding."""
        keys: list[tuple[str, set[str]]] = []

        def _add_key(raw_value: str | None, roles: set[str]) -> None:
            token = str(raw_value or "").strip()
            if token:
                keys.append((token, {_canonical_role(role) for role in roles}))

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
                    keys.append((token, {_canonical_role(role) for role in roles}))

        _add_key(
            _config_or_env("index.auth.admin_api_key", "CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY"),
            {"admin"},
        )
        _add_key(
            _config_or_env("index.auth.maintainer_api_key", "CLOUD_DOG__INDEX__AUTH__MAINTAINER_API_KEY"),
            {"user"},
        )
        _add_key(
            _config_or_env("index.auth.writer_api_key", "CLOUD_DOG__INDEX__AUTH__WRITER_API_KEY"),
            {"user"},
        )
        _add_key(
            _config_or_env("index.auth.reader_api_key", "CLOUD_DOG__INDEX__AUTH__READER_API_KEY"),
            {"viewer"},
        )

        a2a_key = _config_or_env(
            "test.a2a_api_key",
            "TEST_A2A_API_KEY",
        )
        if a2a_key:
            keys.append((a2a_key, {"admin"}))

        return keys

    def _seed_configured_keys(self, injected_keys: dict[str, set[str]] | None = None) -> None:
        configured = (
            [(key, {_canonical_role(role) for role in roles}) for key, roles in injected_keys.items()]
            if injected_keys is not None
            else self._configured_key_roles()
        )
        for raw_key, roles in configured:
            self.register_api_key(raw_key, roles=roles, owner_user_id=f"configured:{hash_api_key(raw_key)[:12]}")

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

    def register_api_key(
        self,
        raw_key: str,
        *,
        roles: set[str],
        owner_user_id: str | None = None,
        key_id: str | None = None,
    ) -> str:
        """Register a configured key in cloud_dog_idam's hashed key manager."""
        clean_key = str(raw_key or "").strip()
        if not clean_key:
            raise ValueError("raw_key is required")
        api_key_id = key_id or str(uuid4())
        user_id = owner_user_id or f"api-key:{hash_api_key(clean_key)[:12]}"
        user_roles = {_canonical_role(role) for role in roles} or {"viewer"}
        primary_role = "admin" if "admin" in user_roles else ("user" if "user" in user_roles else "viewer")
        self._users[user_id] = IDAMUser(
            user_id=user_id,
            username=user_id,
            role=primary_role,
            status=IDAMUserStatus.ACTIVE,
            is_system_user=True,
        )
        for role in user_roles:
            self._rbac.assign_role_to_user(user_id, role)
        self._api_key_manager._keys[api_key_id] = IDAMApiKey(
            api_key_id=api_key_id,
            owner_user_id=user_id,
            key_prefix=clean_key[:3],
            key_hash=hash_api_key(clean_key),
            status="active",
        )
        return api_key_id

    def bind_api_key_manager(self, manager: Any) -> None:
        """Use the service's canonical IDAM key manager for runtime-created keys."""
        if manager is self._api_key_manager:
            return
        for key_id, item in getattr(self._api_key_manager, "_keys", {}).items():
            getattr(manager, "_keys", {})[key_id] = item
        self._api_key_manager = manager
        self._provider = APIKeyProvider(self._api_key_manager, self._users.get)

    def sync_identity_roles(self, user_id: str, roles: set[str], *, enabled: bool = True) -> None:
        """Synchronise service user/group roles into the IDAM RBAC engine."""
        clean_roles = {_canonical_role(role) for role in roles} or {"viewer"}
        primary_role = "admin" if "admin" in clean_roles else ("user" if "user" in clean_roles else "viewer")
        status = IDAMUserStatus.ACTIVE if enabled else IDAMUserStatus.DISABLED
        self._users[user_id] = IDAMUser(
            user_id=user_id,
            username=user_id,
            role=primary_role,
            status=status,
            is_system_user=False,
        )
        for role in clean_roles:
            self._rbac.assign_role_to_user(user_id, role)

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

        thread = getattr(__import__("threading"), "Thread")(target=_runner, daemon=True)
        thread.start()
        thread.join()
        ok, value = result_queue.get()
        if ok:
            return value
        raise value

    def api_key_identity(self, headers: dict[str, str]) -> AuthResult:
        """Authenticate using cloud_dog_idam API-key verification."""
        # Covers: FR-04, FR-01B
        key = self._resolve_api_key(headers)
        if not key:
            raise PermissionError("Authentication failed")

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

        user_id = str(result.user.user_id)
        roles = self._rbac.get_effective_roles(user_id) or {_canonical_role(result.user.role)}
        permissions = self._rbac.get_effective_permissions(user_id)
        # Reject disabled users — check the service user store if available
        if hasattr(self, '_user_store') and self._user_store is not None:
            user_record = self._user_store.get(user_id)
            if user_record is not None and not getattr(user_record, 'enabled', True):
                raise PermissionError("User account is disabled")
        return AuthResult(
            user_id=user_id,
            roles=roles,
            permissions=permissions,
            token_type="api_key",
        )

    def identity_from_headers(self, headers: dict[str, str]) -> AuthResult:
        """Authenticate API-key or JWT bearer credentials via cloud_dog_idam."""
        try:
            return self.api_key_identity(headers)
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
            roles = {_canonical_role(role_claim)}
        else:
            roles = {_canonical_role(str(item)) for item in role_claim if str(item).strip()}
        if not roles:
            roles = {"viewer"}
        user_id = str(claims.get("sub", claims.get("user_id", "jwt-user")))
        self.sync_identity_roles(user_id, roles)
        return AuthResult(
            user_id=user_id,
            roles=self._rbac.get_effective_roles(user_id),
            permissions=self._rbac.get_effective_permissions(user_id),
            token_type="jwt",
        )

    def require_permission(self, identity: AuthResult, permission: str) -> None:
        """Authorise through cloud_dog_idam RBAC permission state."""
        # Covers: FR-05
        if self._rbac.has_permission(identity.user_id, permission):
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
    process_env = dict(os.environ)
    for env_name in env_names:
        value = str(process_env.get(env_name, "")).strip()
        if value:
            return value

    try:
        from cloud_dog_config import get_config, load_config  # type: ignore
        from index_tools.config.loader import secret_backend_kwarg
    except Exception:
        return ""

    candidates = [config_key, *env_names, *(name.replace("__", ".").lower() for name in env_names)]
    for candidate in candidates:
        try:
            value = get_config(candidate)
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return str(value).strip()

    try:
        compiled = load_config(unresolved_policy="strict", **secret_backend_kwarg(False))
    except Exception:
        return ""
    for candidate in candidates:
        try:
            value = compiled.get(candidate)
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""

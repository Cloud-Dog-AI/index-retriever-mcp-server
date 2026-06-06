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

# index-retriever-mcp-server - Bootstrap-seed loader (W28A-F-RF-07-L3)

"""Bootstrap-seed loader for durable index-retriever admin state.

The seed file is a small YAML document with this shape::

    bootstrap:
      groups:
        - name: ragflow
          roles: [reader, writer]
      users:
        - username: gary
          groups: [ragflow]
          roles: [maintainer, ragflow0-access, tb-access]
      collections:
        - name: ragflow0
          allowed_roles: [admin, ragflow0-access]
      api_keys:
        - name: gary-ragflow-scoped
          username: gary
          token_env_var: INDEX_RETRIEVER_ADMIN_API_KEY

Token values are not stored in the seed file. At apply time, each token is
read from the named process environment variable. If an api-key seed references
an unset variable, the apply fails fast instead of starting with incomplete
admin state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from cloud_dog_config.yaml_loader import load_yaml as _load_yaml


def _cfg_get(key: str, default: str = "") -> str:
    """Resolve an env-var-style key via cloud_dog_config.get_config().

    Resolution order:
    1. ``cloud_dog_config.get_config(key)`` for config files and env overrides.
    2. Process environment for ordinary runtime variables.
    3. *default* when neither source has a value.
    """
    try:
        from cloud_dog_config import get_config  # type: ignore
    except Exception:  # pragma: no cover
        get_config = None  # type: ignore[assignment]
    if get_config is not None:
        try:
            value = get_config(key)
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return str(value)

    import os

    env_val = str(os.environ.get(key, "")).strip()
    if env_val:
        return env_val
    return default


def _cfg_truthy(key: str) -> bool:
    value = _cfg_get(key).strip().lower()
    return value in {"1", "true", "yes", "on"}


class BootstrapSeedError(RuntimeError):
    """Raised when the seed cannot be loaded or applied."""


@dataclass(slots=True)
class GroupSeed:
    """Group entity to be seeded into the admin store."""

    name: str
    roles: list[str] = field(default_factory=list)
    members: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UserSeed:
    """User entity to be seeded into the admin store."""

    username: str
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    enabled: bool = True
    display_name: str | None = None


@dataclass(slots=True)
class CollectionSeed:
    """Collection entity to be seeded into the admin store."""

    name: str
    profile: str = "default"
    allowed_roles: list[str] = field(default_factory=list)
    description: str = ""


@dataclass(slots=True)
class ApiKeySeed:
    """API-key entity to be seeded into the admin store."""

    name: str
    username: str
    token_env_var: str
    roles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BootstrapSeed:
    """Top-level container for all admin entities to seed."""

    groups: list[GroupSeed] = field(default_factory=list)
    users: list[UserSeed] = field(default_factory=list)
    collections: list[CollectionSeed] = field(default_factory=list)
    api_keys: list[ApiKeySeed] = field(default_factory=list)


def load_seed(path: str | Path) -> BootstrapSeed:
    """Load and parse a bootstrap seed YAML file."""
    seed_path = Path(path)
    if not seed_path.is_file():
        raise BootstrapSeedError(f"Bootstrap seed not found: {seed_path}")
    try:
        raw = _load_yaml(str(seed_path))
    except Exception as exc:
        raise BootstrapSeedError(f"Failed to parse seed YAML at {seed_path}: {exc}") from exc
    if not raw:
        return BootstrapSeed()
    body = raw.get("bootstrap", raw)
    if not isinstance(body, Mapping):
        raise BootstrapSeedError("Seed must contain a 'bootstrap' mapping or be one at root")

    return BootstrapSeed(
        groups=[_coerce_group(item) for item in _seq(body.get("groups"))],
        users=[_coerce_user(item) for item in _seq(body.get("users"))],
        collections=[_coerce_collection(item) for item in _seq(body.get("collections"))],
        api_keys=[_coerce_api_key(item) for item in _seq(body.get("api_keys"))],
    )


def _seq(value: Any) -> Sequence[Any]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    raise BootstrapSeedError(f"Expected a list, got {type(value).__name__}")


def _coerce_group(item: Any) -> GroupSeed:
    if not isinstance(item, Mapping):
        raise BootstrapSeedError(f"Group entry must be a mapping, got {type(item).__name__}")
    name = str(item.get("name") or "").strip()
    if not name:
        raise BootstrapSeedError("Group entry missing 'name'")
    return GroupSeed(
        name=name,
        roles=[str(r) for r in _seq(item.get("roles"))],
        members=[str(m) for m in _seq(item.get("members"))],
    )


def _coerce_user(item: Any) -> UserSeed:
    if not isinstance(item, Mapping):
        raise BootstrapSeedError(f"User entry must be a mapping, got {type(item).__name__}")
    username = str(item.get("username") or item.get("name") or "").strip()
    if not username:
        raise BootstrapSeedError("User entry missing 'username'")
    display_name = item.get("display_name")
    return UserSeed(
        username=username,
        roles=[str(r) for r in _seq(item.get("roles"))],
        groups=[str(g) for g in _seq(item.get("groups"))],
        enabled=bool(item.get("enabled", True)),
        display_name=str(display_name) if display_name is not None else None,
    )


def _coerce_collection(item: Any) -> CollectionSeed:
    if not isinstance(item, Mapping):
        raise BootstrapSeedError(f"Collection entry must be a mapping, got {type(item).__name__}")
    name = str(item.get("name") or "").strip()
    if not name:
        raise BootstrapSeedError("Collection entry missing 'name'")
    return CollectionSeed(
        name=name,
        profile=str(item.get("profile") or "default"),
        allowed_roles=[str(r) for r in _seq(item.get("allowed_roles"))],
        description=str(item.get("description") or ""),
    )


def _coerce_api_key(item: Any) -> ApiKeySeed:
    if not isinstance(item, Mapping):
        raise BootstrapSeedError(f"API-key entry must be a mapping, got {type(item).__name__}")
    name = str(item.get("name") or "").strip()
    username = str(item.get("username") or "").strip()
    token_env_var = str(item.get("token_env_var") or "").strip()
    if not name:
        raise BootstrapSeedError("API-key entry missing 'name'")
    if not username:
        raise BootstrapSeedError(f"API-key '{name}' missing 'username'")
    if not token_env_var:
        raise BootstrapSeedError(f"API-key '{name}' missing 'token_env_var'")
    if "token" in item and item.get("token"):
        raise BootstrapSeedError(
            f"API-key '{name}' contains an inline 'token' value; use 'token_env_var'"
        )
    return ApiKeySeed(
        name=name,
        username=username,
        token_env_var=token_env_var,
        roles=[str(r) for r in _seq(item.get("roles"))],
    )


class EnvTokenResolver:
    """Resolve API-key token values from named process environment variables."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def resolve(self, token_env_var: str) -> str:
        name = str(token_env_var or "").strip()
        if not name:
            raise BootstrapSeedError("API-key token environment variable name is empty")
        if name not in self._cache:
            value = _cfg_get(name).strip()
            if not value:
                raise BootstrapSeedError(
                    f"API-key token environment variable is unset or empty: {name}"
                )
            self._cache[name] = value
        return self._cache[name]


_ADMIN_ROLES: set[str] = {"admin"}
_BOOTSTRAP_ACTOR = "bootstrap-seed"


def apply_seed(
    service: Any,
    seed: BootstrapSeed,
    *,
    token_resolver: EnvTokenResolver | None = None,
) -> dict[str, int]:
    """Apply the seed to the given ``IndexService``."""
    summary = {
        "groups_applied": 0,
        "users_applied": 0,
        "collections_applied": 0,
        "api_keys_applied": 0,
    }

    if seed.api_keys and token_resolver is None:
        token_resolver = EnvTokenResolver()

    for group in seed.groups:
        _apply_group(service, group)
        summary["groups_applied"] += 1

    for user in seed.users:
        _apply_user(service, user)
        summary["users_applied"] += 1

    for collection in seed.collections:
        _apply_collection(service, collection)
        summary["collections_applied"] += 1

    for api_key in seed.api_keys:
        token = token_resolver.resolve(api_key.token_env_var)  # type: ignore[union-attr]
        _apply_api_key(service, api_key, token=token)
        summary["api_keys_applied"] += 1

    return summary


def _apply_group(service: Any, group: GroupSeed) -> None:
    payload: dict[str, Any] = {
        "roles": list(group.roles),
        "members": list(group.members),
    }
    if group.name in service.groups:
        service.admin_group_update(
            group.name,
            roles=_ADMIN_ROLES,
            payload=payload,
            actor=_BOOTSTRAP_ACTOR,
        )
        return
    service.admin_group_create(
        group.name,
        roles=_ADMIN_ROLES,
        payload=payload,
        actor=_BOOTSTRAP_ACTOR,
    )


def _apply_user(service: Any, user: UserSeed) -> None:
    payload: dict[str, Any] = {
        "display_name": user.display_name or user.username,
        "roles": list(user.roles),
        "groups": list(user.groups),
        "enabled": user.enabled,
    }
    if user.username in service.users:
        service.admin_user_update(
            user.username,
            roles=_ADMIN_ROLES,
            payload=payload,
            actor=_BOOTSTRAP_ACTOR,
        )
        return
    service.admin_user_create(
        user.username,
        roles=_ADMIN_ROLES,
        payload=payload,
        actor=_BOOTSTRAP_ACTOR,
    )


def _apply_collection(service: Any, collection: CollectionSeed) -> None:
    collection_key = f"{collection.profile}:{collection.name}"
    allowed_roles = set(collection.allowed_roles) or {"reader", "writer", "maintainer", "admin"}
    if collection_key in service.collections:
        service.admin_collection_update(
            collection.profile,
            collection.name,
            roles=_ADMIN_ROLES,
            updates={
                "description": collection.description,
                "allowed_roles": sorted(allowed_roles),
            },
            actor=_BOOTSTRAP_ACTOR,
        )
        return
    service.admin_collection_create(
        collection.profile,
        collection.name,
        roles=_ADMIN_ROLES,
        payload={"description": collection.description},
        allowed_roles=allowed_roles,
        actor=_BOOTSTRAP_ACTOR,
    )


def _apply_api_key(service: Any, api_key: ApiKeySeed, *, token: str) -> None:
    """Apply an api-key seed entry, idempotent on the (username, token) pair."""
    desired_hash = __import__("hashlib").sha256(token.encode("utf-8")).hexdigest()
    existing = [
        record
        for record in service.api_keys.values()
        if (record.user_id or "") == api_key.username
    ]
    matching = [r for r in existing if getattr(r, "token_hash", "") == desired_hash and not r.revoked]
    if matching:
        return
    for record in existing:
        if not record.revoked and getattr(record, "token_hash", "") != desired_hash:
            record.revoked = True
    payload: dict[str, Any] = {
        "label": api_key.name,
        "user_id": api_key.username,
        "token": token,
    }
    if api_key.roles:
        payload["roles"] = list(api_key.roles)
    service.admin_api_key_create(
        roles=_ADMIN_ROLES,
        payload=payload,
        actor=_BOOTSTRAP_ACTOR,
    )


_SEED_PATH_ENV = "INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH"
_SEED_DISABLED_ENV = "INDEX_RETRIEVER_BOOTSTRAP_SEED_DISABLED"


def resolve_seed_path() -> str | None:
    """Return the active bootstrap seed file path, or None if not configured."""
    if _cfg_truthy(_SEED_DISABLED_ENV):
        return None

    explicit = _cfg_get(_SEED_PATH_ENV).strip()
    if explicit:
        return explicit
    container_default = "/app/config/bootstrap-seed.yaml"
    if Path(container_default).is_file():
        return container_default
    return None


def maybe_apply_bootstrap_seed(service: Any) -> dict[str, int] | None:
    """Locate, load, and apply the bootstrap seed if one is configured."""
    path = resolve_seed_path()
    if path is None:
        return None
    seed = load_seed(path)
    return apply_seed(service, seed)

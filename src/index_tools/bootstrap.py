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

# index-retriever-mcp-server — Bootstrap-seed loader (W28A-F-RF-07-L3)
#
# Licence: Apache 2.0
# Owner: Cloud-Dog AI
# Description:
#   Durable admin-state seeding for index-retriever-mcp-server. Each of the four
#   service processes (api_server, web_server, mcp_server, a2a_server) holds an
#   independent ``IndexService()`` with in-memory admin stores (users, groups,
#   collections, api-keys). On container restart, those stores reset to empty.
#   This module loads a seed YAML and applies the desired admin state on every
#   ``IndexService.__init__`` so the in-memory stores re-converge to the same
#   stable identities after every restart.
#
# Related requirements: F-RF-07-L3 + F-RF-07-L4 closure (RULES.md §12 durability;
#   AGENT-LESSONS.md §6.26 commit discipline).
# Related architecture: persistent admin state via bootstrap-seed (Option 1).
# Related tests: tests/unit/UT_Bootstrap/test_bootstrap_seed_apply.py.
#
# Recent changes:
# - 2026-04-24: W28A-F-RF-07-L3-APPLY initial implementation.

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
          token_vault_path: "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"

Token values are NEVER stored in the seed file — only Vault path references.
At apply-time, the loader reads each token from Vault using the service's
``VAULT_ADDR`` / ``VAULT_TOKEN`` / ``VAULT_MOUNT_POINT`` environment variables.
If Vault is unreachable AND there are tokens that need resolving, the apply
fails fast (per the F-RF-07-L3 directive: NO silent empty-state start).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from cloud_dog_config.yaml_loader import load_yaml as _load_yaml


def _cfg_get(key: str, default: str = "") -> str:
    """Resolve an env-var-style key via cloud_dog_config.get_config().

    Resolution order:
    1. ``cloud_dog_config.get_config(key)`` -- covers config.yaml / defaults.yaml
       / env-file / CLOUD_DOG__ namespace env vars.
    2. Process environment (for standard vars like VAULT_ADDR, VAULT_TOKEN,
       REQUESTS_CA_BUNDLE that live outside the config hierarchy).
    3. *default* when neither source has a value.

    This replaces all former direct-env-read calls in this module
    (RULES S2.4 / AGENT-LESSONS S6.19-S6.20).
    """
    # 1. Try cloud_dog_config first (canonical path).
    try:
        from cloud_dog_config import get_config  # type: ignore  # config.get
    except Exception:  # pragma: no cover
        get_config = None  # type: ignore[assignment]
    if get_config is not None:
        try:
            value = get_config(key)
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return str(value)
    # 2. Fallback: process environment for non-config-hierarchy keys.
    import os  # config.get
    _env = dict(os.environ)
    env_val = str(_env.get(key, "")).strip()
    if env_val:
        return env_val
    return default


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
    """API-key entity to be seeded into the admin store.

    The token value is NOT stored here — only its Vault path. The apply loop
    resolves the path against the live Vault at apply-time.
    """

    name: str
    username: str
    token_vault_path: str
    roles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BootstrapSeed:
    """Top-level container for all admin entities to seed."""

    groups: list[GroupSeed] = field(default_factory=list)
    users: list[UserSeed] = field(default_factory=list)
    collections: list[CollectionSeed] = field(default_factory=list)
    api_keys: list[ApiKeySeed] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Loader
# ──────────────────────────────────────────────────────────────────────────────


def load_seed(path: str | Path) -> BootstrapSeed:
    """Load and parse a bootstrap seed YAML file.

    Args:
        path: Filesystem path to the seed YAML.

    Returns:
        A ``BootstrapSeed`` populated from the file.

    Raises:
        BootstrapSeedError: If the file cannot be read or has invalid shape.
    """
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
        raise BootstrapSeedError("Seed must contain a 'bootstrap' mapping (or be one at root)")

    groups = [_coerce_group(item) for item in _seq(body.get("groups"))]
    users = [_coerce_user(item) for item in _seq(body.get("users"))]
    collections = [_coerce_collection(item) for item in _seq(body.get("collections"))]
    api_keys = [_coerce_api_key(item) for item in _seq(body.get("api_keys"))]
    return BootstrapSeed(
        groups=groups,
        users=users,
        collections=collections,
        api_keys=api_keys,
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
    enabled = item.get("enabled", True)
    display_name = item.get("display_name")
    return UserSeed(
        username=username,
        roles=[str(r) for r in _seq(item.get("roles"))],
        groups=[str(g) for g in _seq(item.get("groups"))],
        enabled=bool(enabled),
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
    token_vault_path = str(item.get("token_vault_path") or "").strip()
    if not name:
        raise BootstrapSeedError("API-key entry missing 'name'")
    if not username:
        raise BootstrapSeedError(f"API-key '{name}' missing 'username'")
    if not token_vault_path:
        raise BootstrapSeedError(f"API-key '{name}' missing 'token_vault_path'")
    # §9.2 — refuse plaintext tokens in the seed file
    if "token" in item and item.get("token"):
        raise BootstrapSeedError(
            f"API-key '{name}' contains an inline 'token' value — only 'token_vault_path' is permitted (§9.2)"
        )
    return ApiKeySeed(
        name=name,
        username=username,
        token_vault_path=token_vault_path,
        roles=[str(r) for r in _seq(item.get("roles"))],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Vault token resolver
# ──────────────────────────────────────────────────────────────────────────────


class _HttpVaultClient:
    """Minimal HTTP-only Vault KV-v2 client used as a fallback when ``hvac``
    is not installed in the runtime image.

    Only implements the ``read(path)`` surface that ``VaultTokenResolver``
    needs. Returns the data dict (envelope-aware in the resolver layer).
    """

    def __init__(self, *, addr: str, token: str, mount: str) -> None:
        self._addr = addr.rstrip("/")
        self._token = token
        self._mount = (mount or "").strip("/")

    def read(self, path: str) -> dict[str, Any] | None:
        # path is e.g. "secret/cloud_dog_ai/config" — convert to KV-v2 URL.
        # KV-v2 layout: GET <addr>/v1/<mount>/data/<rest>
        # If path starts with "secret/", strip it and reuse the explicit mount.
        rest = path
        if rest.startswith("secret/"):
            rest = rest[len("secret/") :]
        # If rest starts with the mount + "/", strip that to avoid duplication.
        if self._mount and rest.startswith(self._mount + "/"):
            rest = rest[len(self._mount) + 1 :]
        mount = self._mount or "secret"
        url = f"{self._addr}/v1/{mount}/data/{rest}"
        try:
            import requests  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise BootstrapSeedError(f"requests unavailable for HTTP Vault read: {exc}") from exc
        resp = requests.get(
            url,
            headers={"X-Vault-Token": self._token},
            timeout=10.0,
            verify=_cfg_get("REQUESTS_CA_BUNDLE") or True,
        )
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise BootstrapSeedError(
                f"Vault HTTP read {url} -> {resp.status_code}: {resp.text[:200]}"
            )
        body = resp.json()
        # KV-v2 response: {"data": {"data": <secret-body>, "metadata": {...}}}
        data = body.get("data", {})
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data


class VaultTokenResolver:
    """Resolve ``token_vault_path`` references against live Vault.

    The path format is ``<kv-path>:<dotted.json.path>``, e.g.
    ``config:dev.services.index-retriever.gary_api_key`` when the active
    Vault mount is already ``cloud_dog_ai``.

    The KV path is read via the platform ``VaultClient`` using the active
    ``VAULT_ADDR`` / ``VAULT_TOKEN`` env vars. The KV value is expected to be
    either a dict or a ``{"json": "<json-string>"}`` envelope (the platform's
    canonical config layout); the dotted path then traverses the parsed object.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        self._cache: dict[str, str] = {}

    @classmethod
    def from_environment(cls) -> "VaultTokenResolver":
        """Construct a resolver using ``VAULT_ADDR`` / ``VAULT_TOKEN`` env vars.

        Tries the platform ``cloud_dog_config.vault.client.VaultClient`` first
        (which depends on ``hvac``). If hvac is unavailable in the container's
        Python deps, falls back to a minimal HTTP-only client that reads the
        Vault KV-v2 endpoint via ``requests``. Either way, the contract is the
        same: ``read(path) -> dict | str | None``.

        Returns a resolver whose ``_client`` is None if env vars are missing —
        that's only OK if no api-keys need resolving. ``apply_seed`` calls
        ``ensure_available`` before resolving any path.
        """
        addr = _cfg_get("VAULT_ADDR").strip()
        token = _cfg_get("VAULT_TOKEN").strip()
        if not addr or not token:
            return cls(client=None)
        mount = _cfg_get("VAULT_MOUNT_POINT").strip()
        # Preferred path: platform VaultClient (hvac-backed).
        try:
            from cloud_dog_config.vault.client import VaultClient, VaultConnectionConfig
            client = VaultClient(
                VaultConnectionConfig(
                    server=addr,
                    token=token,
                    timeout_seconds=10.0,
                    mount_point=mount,
                )
            )
            return cls(client=client)
        except Exception:
            # hvac may be missing — fall back to direct HTTP.
            pass
        try:
            client = _HttpVaultClient(addr=addr, token=token, mount=mount)
            return cls(client=client)
        except Exception:
            return cls(client=None)

    def ensure_available(self) -> None:
        """Fail fast if no Vault client is available."""
        if self._client is None:
            raise BootstrapSeedError(
                "Vault unreachable: VAULT_ADDR/VAULT_TOKEN not set or VaultClient unavailable. "
                "Bootstrap seed contains api_keys whose tokens MUST be resolved from Vault. "
                "Refusing to start with empty admin state (F-RF-07-L3 directive)."
            )

    def resolve(self, token_vault_path: str) -> str:
        """Resolve a ``<kv-path>:<dotted.path>`` Vault reference to a token string."""
        if token_vault_path in self._cache:
            return self._cache[token_vault_path]
        self.ensure_available()
        if ":" not in token_vault_path:
            raise BootstrapSeedError(
                f"token_vault_path missing ':' separator: {token_vault_path}"
            )
        kv_path, _, dotted = token_vault_path.partition(":")
        kv_path = kv_path.strip()
        dotted = dotted.strip()
        if not kv_path or not dotted:
            raise BootstrapSeedError(
                f"Invalid token_vault_path '{token_vault_path}' — need '<kv-path>:<dotted.path>'"
            )
        if not kv_path.startswith("secret/"):
            kv_path = f"secret/{kv_path}"
        try:
            data = self._client.read(kv_path)  # type: ignore[union-attr]
        except Exception as exc:
            raise BootstrapSeedError(
                f"Vault read failed for {kv_path}: {exc}"
            ) from exc
        if data is None:
            raise BootstrapSeedError(f"Vault path not found: {kv_path}")
        # The platform Vault layout can wrap the body as either
        # {"json": "<json-string>"}, {"json": {...}}, or {"content": "<json>"}.
        while isinstance(data, Mapping):
            if isinstance(data.get("json"), str):
                try:
                    data = json.loads(data["json"])
                except Exception as exc:
                    raise BootstrapSeedError(
                        f"Failed to parse Vault json envelope at {kv_path}: {exc}"
                    ) from exc
                continue
            if isinstance(data.get("json"), Mapping):
                data = data["json"]
                continue
            if isinstance(data.get("content"), str):
                try:
                    data = json.loads(data["content"])
                except Exception as exc:
                    raise BootstrapSeedError(
                        f"Failed to parse Vault content envelope at {kv_path}: {exc}"
                    ) from exc
                continue
            break
        if not isinstance(data, Mapping):
            raise BootstrapSeedError(
                f"Vault content at {kv_path} is not a mapping (got {type(data).__name__})"
            )
        cursor: Any = data
        for segment in dotted.split("."):
            if not isinstance(cursor, Mapping):
                raise BootstrapSeedError(
                    f"Cannot traverse '{segment}' under non-mapping at {kv_path}:{dotted}"
                )
            if segment not in cursor:
                raise BootstrapSeedError(
                    f"Vault key '{segment}' not present at {kv_path}:{dotted}"
                )
            cursor = cursor[segment]
        if not isinstance(cursor, str) or not cursor.strip():
            raise BootstrapSeedError(
                f"Resolved value at {kv_path}:{dotted} is empty or not a string"
            )
        resolved = cursor.strip()
        self._cache[token_vault_path] = resolved
        return resolved


# ──────────────────────────────────────────────────────────────────────────────
# Apply
# ──────────────────────────────────────────────────────────────────────────────


_ADMIN_ROLES: set[str] = {"admin"}
_BOOTSTRAP_ACTOR = "bootstrap-seed"


def apply_seed(
    service: Any,
    seed: BootstrapSeed,
    *,
    vault_resolver: VaultTokenResolver | None = None,
) -> dict[str, int]:
    """Apply the seed to the given ``IndexService``.

    Idempotent: if an entity already exists, the apply step is a no-op
    (or an in-place update for users/groups/collections — never a duplicate).

    Args:
        service: An ``IndexService`` instance.
        seed: The parsed ``BootstrapSeed``.
        vault_resolver: Optional resolver; if absent, one is constructed from env.

    Returns:
        A small summary dict with counts (``groups_applied``, ``users_applied``,
        ``collections_applied``, ``api_keys_applied``). Useful for log lines.
    """
    summary = {
        "groups_applied": 0,
        "users_applied": 0,
        "collections_applied": 0,
        "api_keys_applied": 0,
    }

    if seed.api_keys:
        if vault_resolver is None:
            vault_resolver = VaultTokenResolver.from_environment()
        # Fail fast (F-RF-07-L3): never silently start with empty admin state.
        vault_resolver.ensure_available()

    # Groups first — users may reference them.
    for group in seed.groups:
        _apply_group(service, group)
        summary["groups_applied"] += 1

    # Users second — api-keys may reference them.
    for user in seed.users:
        _apply_user(service, user)
        summary["users_applied"] += 1

    # Collections third — independent, but kept after users for log readability.
    for collection in seed.collections:
        _apply_collection(service, collection)
        summary["collections_applied"] += 1

    # API keys last — depend on Vault for tokens, depend on users for owner.
    for api_key in seed.api_keys:
        token = vault_resolver.resolve(api_key.token_vault_path)  # type: ignore[union-attr]
        _apply_api_key(service, api_key, token=token)
        summary["api_keys_applied"] += 1

    return summary


def _apply_group(service: Any, group: GroupSeed) -> None:
    payload: dict[str, Any] = {
        "roles": list(group.roles),
        "members": list(group.members),
    }
    if group.name in service.groups:
        # Idempotent in-place update.
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
        # Idempotent — refresh allowed_roles + description, preserve other metadata.
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
        payload={
            "description": collection.description,
        },
        allowed_roles=allowed_roles,
        actor=_BOOTSTRAP_ACTOR,
    )


def _apply_api_key(service: Any, api_key: ApiKeySeed, *, token: str) -> None:
    """Apply an api-key seed entry, idempotent on the (username, token) pair.

    Idempotency strategy: compare the resolved Vault value by hash only. If a key
    exists for the user but with a different hash (Vault rotation), revoke the old
    record and create a fresh one. Otherwise create.
    """
    desired_token = token
    desired_hash = __import__("hashlib").sha256(desired_token.encode("utf-8")).hexdigest()
    # Find any existing record for this user.
    existing = [
        record for record in service.api_keys.values()
        if (record.user_id or "") == api_key.username
    ]
    matching = [r for r in existing if getattr(r, "token_hash", "") == desired_hash and not r.revoked]
    if matching:
        # Already present with the right token — no-op.
        return
    # Stale/different-token records for this user → revoke them so the new key is canonical.
    for record in existing:
        if not record.revoked and getattr(record, "token_hash", "") != desired_hash:
            record.revoked = True
    payload: dict[str, Any] = {
        "label": api_key.name,
        "user_id": api_key.username,
        "token": desired_token,
    }
    if api_key.roles:
        payload["roles"] = list(api_key.roles)
    service.admin_api_key_create(
        roles=_ADMIN_ROLES,
        payload=payload,
        actor=_BOOTSTRAP_ACTOR,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Init-time entrypoint
# ──────────────────────────────────────────────────────────────────────────────


_SEED_PATH_ENV = "INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH"


def resolve_seed_path() -> str | None:
    """Return the active bootstrap seed file path, or None if not configured.

    Resolution order:
    1. ``INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH`` env var (explicit override)
    2. ``/app/config/bootstrap-seed.yaml`` (container-baked default;
       only this exact path is auto-discovered, NOT a search-up from
       the source tree, so dev workstations don't accidentally apply
       a seed and tests that don't want it stay unaffected).

    Returns None if no candidate exists. Callers MUST treat None as "no
    seeding configured" (a valid local-dev state) — the fail-fast guard is
    only triggered when a seed file exists AND it contains api-keys AND
    Vault is unavailable.
    """
    explicit = _cfg_get(_SEED_PATH_ENV).strip()
    if explicit:
        return explicit
    container_default = "/app/config/bootstrap-seed.yaml"
    if Path(container_default).is_file():
        return container_default
    return None


def maybe_apply_bootstrap_seed(service: Any) -> dict[str, int] | None:
    """Locate + load + apply the bootstrap seed if one is configured.

    Returns the apply summary dict, or None if no seed was configured. Errors
    propagate — caller (``IndexService.__init__``) decides whether to crash
    the process. Per F-RF-07-L3, the answer is YES (fail fast).
    """
    path = resolve_seed_path()
    if path is None:
        return None
    seed = load_seed(path)
    return apply_seed(service, seed)

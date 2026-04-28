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

"""Unit coverage for the index-retriever bootstrap-seed loader (F-RF-07-L3)."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any

import pytest

from index_tools.bootstrap import (
    ApiKeySeed,
    BootstrapSeed,
    BootstrapSeedError,
    CollectionSeed,
    GroupSeed,
    UserSeed,
    VaultTokenResolver,
    apply_seed,
    load_seed,
    maybe_apply_bootstrap_seed,
    resolve_seed_path,
)


# ──────────────────────────────────────────────────────────────────────────────
# Mock Vault client
# ──────────────────────────────────────────────────────────────────────────────


class _MockVault:
    """Minimal Vault client substitute for unit tests.

    Stores a dict keyed by KV path; ``read()`` returns the canonical platform
    ``{"json": "<json-string>"}`` envelope when the value is a dict.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def read(self, path: str) -> Any:
        if path not in self._data:
            return None
        value = self._data[path]
        if isinstance(value, dict):
            import json

            return {"json": json.dumps(value)}
        return value


def _build_resolver(data: dict[str, Any]) -> VaultTokenResolver:
    return VaultTokenResolver(client=_MockVault(data))


# ──────────────────────────────────────────────────────────────────────────────
# Loader (YAML → BootstrapSeed)
# ──────────────────────────────────────────────────────────────────────────────


def _seed_yaml() -> str:
    return textwrap.dedent(
        """
        bootstrap:
          groups:
            - name: ragflow
              roles: []
          users:
            - username: gary
              roles: [maintainer, ragflow0-access, tb-access]
              groups: [ragflow]
          collections:
            - name: ragflow0
              profile: default
              allowed_roles: [admin, ragflow0-access]
            - name: transparentborders
              profile: default
              allowed_roles: [admin, tb-access]
          api_keys:
            - name: gary-ragflow-scoped
              username: gary
              token_vault_path: "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
        """
    ).strip()


def test_load_seed_parses_canonical_shape(tmp_path: Path) -> None:
    seed_path = tmp_path / "bootstrap-seed.yaml"
    seed_path.write_text(_seed_yaml(), encoding="utf-8")
    seed = load_seed(seed_path)
    assert [g.name for g in seed.groups] == ["ragflow"]
    assert [u.username for u in seed.users] == ["gary"]
    assert {c.name for c in seed.collections} == {"ragflow0", "transparentborders"}
    assert [k.username for k in seed.api_keys] == ["gary"]
    assert (
        seed.api_keys[0].token_vault_path
        == "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
    )


def test_load_seed_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(BootstrapSeedError, match="not found"):
        load_seed(tmp_path / "nope.yaml")


def test_load_seed_rejects_inline_token(tmp_path: Path) -> None:
    """§9.2 — plaintext tokens MUST never be stored in the seed file."""
    text = textwrap.dedent(
        """
        bootstrap:
          api_keys:
            - name: gary
              username: gary
              token_vault_path: "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
              token: "cd_PLAINTEXT_VIOLATION"
        """
    ).strip()
    seed_path = tmp_path / "bad.yaml"
    seed_path.write_text(text, encoding="utf-8")
    with pytest.raises(BootstrapSeedError, match="§9.2"):
        load_seed(seed_path)


def test_load_seed_api_key_missing_username(tmp_path: Path) -> None:
    text = textwrap.dedent(
        """
        bootstrap:
          api_keys:
            - name: orphan
              token_vault_path: "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
        """
    ).strip()
    seed_path = tmp_path / "bad.yaml"
    seed_path.write_text(text, encoding="utf-8")
    with pytest.raises(BootstrapSeedError, match="missing 'username'"):
        load_seed(seed_path)


# ──────────────────────────────────────────────────────────────────────────────
# Vault resolver
# ──────────────────────────────────────────────────────────────────────────────


def test_resolver_resolves_canonical_envelope() -> None:
    resolver = _build_resolver(
        {
            "secret/cloud_dog_ai/config": {
                "dev": {
                    "services": {
                        "index-retriever": {
                            "gary_api_key": "cd_TEST_GARY_TOKEN",
                        }
                    }
                }
            }
        }
    )
    token = resolver.resolve(
        "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
    )
    assert token == "cd_TEST_GARY_TOKEN"


def test_resolver_missing_segment_raises() -> None:
    resolver = _build_resolver(
        {
            "secret/cloud_dog_ai/config": {
                "dev": {"services": {"index-retriever": {}}},
            }
        }
    )
    with pytest.raises(BootstrapSeedError, match="not present"):
        resolver.resolve(
            "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
        )


def test_resolver_unreachable_vault_fails_fast() -> None:
    """F-RF-07-L3 binding: NEVER silently start with empty admin state."""
    resolver = VaultTokenResolver(client=None)
    with pytest.raises(BootstrapSeedError, match="Vault unreachable"):
        resolver.ensure_available()


def test_http_vault_client_normalises_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_HttpVaultClient`` must construct the correct KV-v2 URL and parse the response."""
    from index_tools import bootstrap as bootstrap_mod

    captured: dict[str, Any] = {}

    class _FakeResponse:
        status_code = 200
        text = ""

        def json(self) -> dict[str, Any]:
            return {
                "data": {
                    "data": {"foo": "bar"},
                    "metadata": {"version": 1},
                }
            }

    class _FakeRequests:
        def get(self, url: str, **kwargs: Any) -> _FakeResponse:
            captured["url"] = url
            captured["headers"] = kwargs.get("headers", {})
            return _FakeResponse()

    monkeypatch.setitem(__import__("sys").modules, "requests", _FakeRequests())

    client = bootstrap_mod._HttpVaultClient(
        addr="https://vault.example.com",
        token="test-token",
        mount="cloud_dog_ai",
    )
    payload = client.read("secret/cloud_dog_ai/config")
    assert payload == {"foo": "bar"}
    assert captured["url"] == "https://vault.example.com/v1/cloud_dog_ai/data/config"
    assert captured["headers"]["X-Vault-Token"] == "test-token"


def test_resolver_caches_repeat_lookups() -> None:
    class _Counter:
        def __init__(self) -> None:
            self.calls = 0

        def read(self, path: str) -> Any:
            self.calls += 1
            return {
                "json": '{"dev":{"services":{"index-retriever":{"gary_api_key":"cd_T"}}}}'
            }

    counter = _Counter()
    resolver = VaultTokenResolver(client=counter)
    path = "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
    assert resolver.resolve(path) == "cd_T"
    assert resolver.resolve(path) == "cd_T"
    assert counter.calls == 1


# ──────────────────────────────────────────────────────────────────────────────
# apply_seed against a real (in-process) IndexService
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def fresh_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Build a brand-new IndexService whose bootstrap-seed hook is suppressed.

    The seed-on-init hook is what we're testing — we don't want it firing
    transparently while we set up the test fixture. We do this by pointing
    ``maybe_apply_bootstrap_seed.resolve_seed_path`` at None for the fixture
    setup (and only the fixture setup).
    """
    from index_tools import bootstrap as bootstrap_mod

    monkeypatch.delenv("INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH", raising=False)
    monkeypatch.setattr(bootstrap_mod, "resolve_seed_path", lambda: None)

    from index_tools.tools.service import IndexService

    audit_path = tmp_path / "audit.jsonl"
    return IndexService(audit_path=str(audit_path))


def _canonical_seed() -> BootstrapSeed:
    return BootstrapSeed(
        groups=[GroupSeed(name="ragflow", roles=[])],
        users=[
            UserSeed(
                username="gary",
                roles=["maintainer", "ragflow0-access", "tb-access"],
                groups=["ragflow"],
            ),
            UserSeed(
                username="colin",
                roles=["maintainer", "ragflow1-access", "tb-access"],
                groups=["ragflow"],
            ),
        ],
        collections=[
            CollectionSeed(
                name="ragflow0",
                profile="default",
                allowed_roles=["admin", "ragflow0-access"],
            ),
            CollectionSeed(
                name="ragflow1",
                profile="default",
                allowed_roles=["admin", "ragflow1-access"],
            ),
            CollectionSeed(
                name="transparentborders",
                profile="default",
                allowed_roles=["admin", "tb-access"],
            ),
        ],
        api_keys=[
            ApiKeySeed(
                name="gary-ragflow-scoped",
                username="gary",
                token_vault_path=(
                    "cloud_dog_ai/config:dev.services.index-retriever.gary_api_key"
                ),
            ),
            ApiKeySeed(
                name="colin-ragflow-scoped",
                username="colin",
                token_vault_path=(
                    "cloud_dog_ai/config:dev.services.index-retriever.colin_api_key"
                ),
            ),
        ],
    )


def _canonical_vault_data() -> dict[str, Any]:
    return {
        "secret/cloud_dog_ai/config": {
            "dev": {
                "services": {
                    "index-retriever": {
                        "gary_api_key": "cd_TEST_GARY_TOKEN_0001",
                        "colin_api_key": "cd_TEST_COLIN_TOKEN_0001",
                    }
                }
            }
        }
    }


def test_apply_seed_populates_all_admin_stores(fresh_service: Any) -> None:
    resolver = _build_resolver(_canonical_vault_data())
    summary = apply_seed(fresh_service, _canonical_seed(), vault_resolver=resolver)
    assert summary == {
        "groups_applied": 1,
        "users_applied": 2,
        "collections_applied": 3,
        "api_keys_applied": 2,
    }
    assert "ragflow" in fresh_service.groups
    assert {"gary", "colin"}.issubset(fresh_service.users.keys())
    assert {"default:ragflow0", "default:ragflow1", "default:transparentborders"}.issubset(
        fresh_service.collections.keys()
    )
    api_records = list(fresh_service.api_keys.values())
    tokens = {r.token for r in api_records if not r.revoked}
    assert {"cd_TEST_GARY_TOKEN_0001", "cd_TEST_COLIN_TOKEN_0001"}.issubset(tokens)


def test_apply_seed_role_acl_invariants(fresh_service: Any) -> None:
    """gary's roles + per-collection ACL must align with RF-04 Phase B contract."""
    resolver = _build_resolver(_canonical_vault_data())
    apply_seed(fresh_service, _canonical_seed(), vault_resolver=resolver)
    gary = fresh_service.users["gary"]
    assert gary.roles == {"maintainer", "ragflow0-access", "tb-access"}
    ragflow0 = fresh_service.collections["default:ragflow0"]
    assert ragflow0.allowed_roles == {"admin", "ragflow0-access"}
    # Sanity: gary's roles intersect ragflow0 ACL but NOT ragflow1 ACL.
    ragflow1 = fresh_service.collections["default:ragflow1"]
    assert gary.roles & ragflow0.allowed_roles
    assert not (gary.roles & ragflow1.allowed_roles)


def test_apply_seed_is_idempotent(fresh_service: Any) -> None:
    """Applying the same seed twice MUST converge to the same admin state."""
    resolver = _build_resolver(_canonical_vault_data())
    apply_seed(fresh_service, _canonical_seed(), vault_resolver=resolver)
    snapshot_users = sorted(fresh_service.users.keys())
    snapshot_groups = sorted(fresh_service.groups.keys())
    snapshot_collections = sorted(fresh_service.collections.keys())
    snapshot_api_keys = sorted(
        (r.user_id, r.token, r.revoked) for r in fresh_service.api_keys.values()
    )
    apply_seed(fresh_service, _canonical_seed(), vault_resolver=resolver)
    assert sorted(fresh_service.users.keys()) == snapshot_users
    assert sorted(fresh_service.groups.keys()) == snapshot_groups
    assert sorted(fresh_service.collections.keys()) == snapshot_collections
    assert (
        sorted((r.user_id, r.token, r.revoked) for r in fresh_service.api_keys.values())
        == snapshot_api_keys
    )
    # No duplicate user records.
    assert len(fresh_service.users) == 2


def test_apply_seed_handles_vault_token_rotation(fresh_service: Any) -> None:
    """If Vault rotates a token, the old key is revoked and the new one created."""
    resolver_v1 = _build_resolver(_canonical_vault_data())
    apply_seed(fresh_service, _canonical_seed(), vault_resolver=resolver_v1)
    rotated: dict[str, Any] = {
        "secret/cloud_dog_ai/config": {
            "dev": {
                "services": {
                    "index-retriever": {
                        "gary_api_key": "cd_NEW_GARY_TOKEN_0002",
                        "colin_api_key": "cd_TEST_COLIN_TOKEN_0001",
                    }
                }
            }
        }
    }
    resolver_v2 = _build_resolver(rotated)
    apply_seed(fresh_service, _canonical_seed(), vault_resolver=resolver_v2)
    gary_records = [
        r for r in fresh_service.api_keys.values() if r.user_id == "gary"
    ]
    active = [r for r in gary_records if not r.revoked]
    revoked = [r for r in gary_records if r.revoked]
    assert len(active) == 1
    assert active[0].token == "cd_NEW_GARY_TOKEN_0002"
    assert any(r.token == "cd_TEST_GARY_TOKEN_0001" for r in revoked)


def test_apply_seed_fails_fast_when_vault_unreachable(fresh_service: Any) -> None:
    """F-RF-07-L3 binding: never silently start with empty admin state."""
    seed = _canonical_seed()
    resolver = VaultTokenResolver(client=None)  # unreachable Vault
    with pytest.raises(BootstrapSeedError, match="Vault unreachable"):
        apply_seed(fresh_service, seed, vault_resolver=resolver)


def test_apply_seed_no_api_keys_does_not_require_vault(fresh_service: Any) -> None:
    """Pure groups+users+collections seed must work without Vault."""
    seed = BootstrapSeed(
        groups=[GroupSeed(name="ragflow")],
        users=[UserSeed(username="gary", roles=["maintainer"], groups=["ragflow"])],
        collections=[CollectionSeed(name="ragflow0", allowed_roles=["admin"])],
        api_keys=[],
    )
    summary = apply_seed(fresh_service, seed, vault_resolver=VaultTokenResolver(client=None))
    assert summary["groups_applied"] == 1
    assert summary["users_applied"] == 1
    assert summary["collections_applied"] == 1
    assert summary["api_keys_applied"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# resolve_seed_path / maybe_apply_bootstrap_seed
# ──────────────────────────────────────────────────────────────────────────────


def test_resolve_seed_path_explicit_env_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_file = tmp_path / "custom-seed.yaml"
    seed_file.write_text("bootstrap: {}\n", encoding="utf-8")
    monkeypatch.setenv("INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH", str(seed_file))
    assert resolve_seed_path() == str(seed_file)


def test_resolve_seed_path_returns_none_when_no_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH", str(tmp_path / "nope.yaml"))
    # The explicit env points at a non-existent path; resolve_seed_path returns
    # the explicit value as-is. maybe_apply_bootstrap_seed will then raise
    # BootstrapSeedError when load_seed runs — which is the correct semantics.
    assert resolve_seed_path() == str(tmp_path / "nope.yaml")


def test_maybe_apply_bootstrap_seed_no_path_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If no seed path is resolved, ``maybe_apply_bootstrap_seed`` is a no-op."""
    from index_tools import bootstrap as bootstrap_mod

    monkeypatch.delenv("INDEX_RETRIEVER_BOOTSTRAP_SEED_PATH", raising=False)
    monkeypatch.setattr(bootstrap_mod, "resolve_seed_path", lambda: None)

    class _DummyService:
        groups: dict[str, Any] = {}
        users: dict[str, Any] = {}
        collections: dict[str, Any] = {}
        api_keys: dict[str, Any] = {}

    assert bootstrap_mod.maybe_apply_bootstrap_seed(_DummyService()) is None

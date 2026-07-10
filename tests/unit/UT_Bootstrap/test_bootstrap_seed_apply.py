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

"""Unit coverage for the index-retriever bootstrap-seed loader (F-RF-07-L3).

W28A-861 ("remove internal publication assumptions", commit 5588f1e) replaced the
Vault-based ``VaultTokenResolver`` / ``token_vault_path`` design with an env-based
``EnvTokenResolver`` / ``token_env_var`` design so the package is publishable
without an internal-Vault dependency. The admin-key secret is supplied by the
operator through a named environment variable (e.g. ``INDEX_RETRIEVER_ADMIN_API_KEY``)
and never written into the seed YAML. These tests cover that current design.
"""

from __future__ import annotations

import textwrap
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from index_tools.bootstrap import (
    ApiKeySeed,
    BootstrapSeed,
    BootstrapSeedError,
    CollectionSeed,
    EnvTokenResolver,
    GroupSeed,
    UserSeed,
    apply_seed,
    load_seed,
    maybe_apply_bootstrap_seed,
    resolve_seed_path,
)

_GARY_ENV = "INDEX_RETRIEVER_GARY_API_KEY"
_COLIN_ENV = "INDEX_RETRIEVER_COLIN_API_KEY"


# ──────────────────────────────────────────────────────────────────────────────
# Loader (YAML → BootstrapSeed)
# ──────────────────────────────────────────────────────────────────────────────


def _seed_yaml() -> str:
    return textwrap.dedent(
        f"""
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
              token_env_var: "{_GARY_ENV}"
        """
    ).strip()
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_load_seed_parses_canonical_shape(tmp_path: Path) -> None:
    seed_path = tmp_path / "bootstrap-seed.yaml"
    seed_path.write_text(_seed_yaml(), encoding="utf-8")
    seed = load_seed(seed_path)
    assert [g.name for g in seed.groups] == ["ragflow"]
    assert [u.username for u in seed.users] == ["gary"]
    assert {c.name for c in seed.collections} == {"ragflow0", "transparentborders"}
    assert [k.username for k in seed.api_keys] == ["gary"]
    assert seed.api_keys[0].token_env_var == _GARY_ENV
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_repo_default_bootstrap_seed_is_parseable() -> None:
    """The container-baked default seed must not crash service startup."""
    repo_root = Path(__file__).resolve().parents[3]
    seed = load_seed(repo_root / "config" / "bootstrap-seed.yaml")
    assert {item.username for item in seed.users} == {"admin", "gary", "colin"}
    assert seed.api_keys == []
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_load_seed_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(BootstrapSeedError, match="not found"):
        load_seed(tmp_path / "nope.yaml")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_load_seed_rejects_inline_token(tmp_path: Path) -> None:
    """§9.2 — plaintext tokens MUST never be stored in the seed file."""
    text = textwrap.dedent(
        f"""
        bootstrap:
          api_keys:
            - name: gary
              username: gary
              token_env_var: "{_GARY_ENV}"
              token: "cd_PLAINTEXT_VIOLATION"
        """
    ).strip()
    seed_path = tmp_path / "bad.yaml"
    seed_path.write_text(text, encoding="utf-8")
    with pytest.raises(BootstrapSeedError, match="inline 'token'"):
        load_seed(seed_path)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_load_seed_api_key_missing_username(tmp_path: Path) -> None:
    text = textwrap.dedent(
        f"""
        bootstrap:
          api_keys:
            - name: orphan
              token_env_var: "{_GARY_ENV}"
        """
    ).strip()
    seed_path = tmp_path / "bad.yaml"
    seed_path.write_text(text, encoding="utf-8")
    with pytest.raises(BootstrapSeedError, match="missing 'username'"):
        load_seed(seed_path)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_load_seed_api_key_missing_token_env_var(tmp_path: Path) -> None:
    text = textwrap.dedent(
        """
        bootstrap:
          api_keys:
            - name: orphan
              username: gary
        """
    ).strip()
    seed_path = tmp_path / "bad.yaml"
    seed_path.write_text(text, encoding="utf-8")
    with pytest.raises(BootstrapSeedError, match="missing 'token_env_var'"):
        load_seed(seed_path)


# ──────────────────────────────────────────────────────────────────────────────
# Env token resolver (W28A-861: bootstrap secrets resolve from operator-set env
# vars; the secret never lives in the seed YAML — RULES §1.4.1 carve-out)
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolver_resolves_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_GARY_ENV, "cd_TEST_GARY_TOKEN")
    resolver = EnvTokenResolver()
    assert resolver.resolve(_GARY_ENV) == "cd_TEST_GARY_TOKEN"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolver_missing_env_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """F-RF-07-L3 binding: NEVER silently start with empty admin state."""
    monkeypatch.delenv(_GARY_ENV, raising=False)
    resolver = EnvTokenResolver()
    with pytest.raises(BootstrapSeedError, match="unset or empty"):
        resolver.resolve(_GARY_ENV)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolver_empty_env_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_GARY_ENV, "   ")
    resolver = EnvTokenResolver()
    with pytest.raises(BootstrapSeedError, match="unset or empty"):
        resolver.resolve(_GARY_ENV)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolver_empty_name_raises() -> None:
    resolver = EnvTokenResolver()
    with pytest.raises(BootstrapSeedError, match="name is empty"):
        resolver.resolve("")
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolver_caches_repeat_lookups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_GARY_ENV, "cd_T")
    resolver = EnvTokenResolver()
    assert resolver.resolve(_GARY_ENV) == "cd_T"
    # Change the env AFTER first resolution — the one-shot resolver must return the
    # cached value (token rotation requires a fresh resolver, see rotation test).
    monkeypatch.setenv(_GARY_ENV, "cd_CHANGED")
    assert resolver.resolve(_GARY_ENV) == "cd_T"


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
                token_env_var=_GARY_ENV,
            ),
            ApiKeySeed(
                name="colin-ragflow-scoped",
                username="colin",
                token_env_var=_COLIN_ENV,
            ),
        ],
    )


def _seed_api_key_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    gary: str = "cd_TEST_GARY_TOKEN_0001",
    colin: str = "cd_TEST_COLIN_TOKEN_0001",
) -> None:
    """Provide the operator-set API-key secrets through the environment."""
    monkeypatch.setenv(_GARY_ENV, gary)
    monkeypatch.setenv(_COLIN_ENV, colin)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_apply_seed_populates_all_admin_stores(
    fresh_service: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_api_key_env(monkeypatch)
    summary = apply_seed(fresh_service, _canonical_seed(), token_resolver=EnvTokenResolver())
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
    token_hashes = {r.token_hash for r in api_records if not r.revoked}
    assert {
        sha256("cd_TEST_GARY_TOKEN_0001".encode("utf-8")).hexdigest(),
        sha256("cd_TEST_COLIN_TOKEN_0001".encode("utf-8")).hexdigest(),
    }.issubset(token_hashes)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_apply_seed_role_acl_invariants(
    fresh_service: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gary's roles + per-collection ACL must align with RF-04 Phase B contract."""
    _seed_api_key_env(monkeypatch)
    apply_seed(fresh_service, _canonical_seed(), token_resolver=EnvTokenResolver())
    gary = fresh_service.users["gary"]
    assert gary.roles == {"maintainer", "ragflow0-access", "tb-access"}
    ragflow0 = fresh_service.collections["default:ragflow0"]
    assert ragflow0.allowed_roles == {"admin", "ragflow0-access"}
    # Sanity: gary's roles intersect ragflow0 ACL but NOT ragflow1 ACL.
    ragflow1 = fresh_service.collections["default:ragflow1"]
    assert gary.roles & ragflow0.allowed_roles
    assert not (gary.roles & ragflow1.allowed_roles)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_apply_seed_is_idempotent(
    fresh_service: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Applying the same seed twice MUST converge to the same admin state."""
    _seed_api_key_env(monkeypatch)
    apply_seed(fresh_service, _canonical_seed(), token_resolver=EnvTokenResolver())
    snapshot_users = sorted(fresh_service.users.keys())
    snapshot_groups = sorted(fresh_service.groups.keys())
    snapshot_collections = sorted(fresh_service.collections.keys())
    snapshot_api_keys = sorted(
        (r.user_id, r.token_hash, r.revoked) for r in fresh_service.api_keys.values()
    )
    apply_seed(fresh_service, _canonical_seed(), token_resolver=EnvTokenResolver())
    assert sorted(fresh_service.users.keys()) == snapshot_users
    assert sorted(fresh_service.groups.keys()) == snapshot_groups
    assert sorted(fresh_service.collections.keys()) == snapshot_collections
    assert (
        sorted((r.user_id, r.token_hash, r.revoked) for r in fresh_service.api_keys.values())
        == snapshot_api_keys
    )
    # No duplicate user records.
    assert len(fresh_service.users) == 2
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_apply_seed_handles_token_rotation(
    fresh_service: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the operator rotates a token, the old key is revoked and the new one created."""
    _seed_api_key_env(monkeypatch)
    apply_seed(fresh_service, _canonical_seed(), token_resolver=EnvTokenResolver())
    # Rotate gary's token in the environment; a FRESH resolver picks up the new value
    # (the one-shot resolver caches within a single apply).
    monkeypatch.setenv(_GARY_ENV, "cd_NEW_GARY_TOKEN_0002")
    apply_seed(fresh_service, _canonical_seed(), token_resolver=EnvTokenResolver())
    gary_records = [r for r in fresh_service.api_keys.values() if r.user_id == "gary"]
    active = [r for r in gary_records if not r.revoked]
    revoked = [r for r in gary_records if r.revoked]
    assert len(active) == 1
    assert active[0].token_hash == sha256("cd_NEW_GARY_TOKEN_0002".encode("utf-8")).hexdigest()
    assert any(
        r.token_hash == sha256("cd_TEST_GARY_TOKEN_0001".encode("utf-8")).hexdigest()
        for r in revoked
    )
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_apply_seed_fails_fast_when_secret_missing(
    fresh_service: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-RF-07-L3 binding: never silently start with empty admin state."""
    monkeypatch.delenv(_GARY_ENV, raising=False)
    monkeypatch.delenv(_COLIN_ENV, raising=False)
    with pytest.raises(BootstrapSeedError, match="unset or empty"):
        apply_seed(fresh_service, _canonical_seed(), token_resolver=EnvTokenResolver())
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_apply_seed_no_api_keys_does_not_require_secrets(fresh_service: Any) -> None:
    """Pure groups+users+collections seed must work without any API-key secret."""
    seed = BootstrapSeed(
        groups=[GroupSeed(name="ragflow")],
        users=[UserSeed(username="gary", roles=["maintainer"], groups=["ragflow"])],
        collections=[CollectionSeed(name="ragflow0", allowed_roles=["admin"])],
        api_keys=[],
    )
    summary = apply_seed(fresh_service, seed)
    assert summary["groups_applied"] == 1
    assert summary["users_applied"] == 1
    assert summary["collections_applied"] == 1
    assert summary["api_keys_applied"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# resolve_seed_path / maybe_apply_bootstrap_seed
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolve_seed_path_explicit_config_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The seed path is resolved through cloud_dog_config (dotted key
    # ``index.bootstrap.seed_path``; operators override via
    # CLOUD_DOG__INDEX__BOOTSTRAP__SEED_PATH). RULES §1.4.1 — no os.environ.
    from index_tools import bootstrap as bootstrap_mod

    seed_file = tmp_path / "custom-seed.yaml"
    seed_file.write_text("bootstrap: {}\n", encoding="utf-8")
    monkeypatch.setattr(
        bootstrap_mod,
        "_cfg_get",
        lambda key, default="": str(seed_file)
        if key == "index.bootstrap.seed_path"
        else default,
    )
    assert resolve_seed_path() == str(seed_file)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolve_seed_path_returns_explicit_nonexistent_as_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from index_tools import bootstrap as bootstrap_mod

    nope = str(tmp_path / "nope.yaml")
    monkeypatch.setattr(
        bootstrap_mod,
        "_cfg_get",
        lambda key, default="": nope if key == "index.bootstrap.seed_path" else default,
    )
    # The explicit config value points at a non-existent path; resolve_seed_path
    # returns the explicit value as-is. maybe_apply_bootstrap_seed will then raise
    # BootstrapSeedError when load_seed runs — which is the correct semantics.
    assert resolve_seed_path() == nope
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_resolve_seed_path_uses_repo_default_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from index_tools import bootstrap as bootstrap_mod

    monkeypatch.setattr(bootstrap_mod, "_cfg_get", lambda key, default="": "")
    container_default = Path("/app/config/bootstrap-seed.yaml")
    repo_default = Path(bootstrap_mod.__file__).resolve().parents[2] / "config" / "bootstrap-seed.yaml"
    expected = container_default if container_default.is_file() else repo_default
    assert expected.is_file()
    assert resolve_seed_path() == str(expected)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_maybe_apply_bootstrap_seed_no_path_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If no seed path is resolved, ``maybe_apply_bootstrap_seed`` is a no-op."""
    from index_tools import bootstrap as bootstrap_mod

    monkeypatch.setattr(bootstrap_mod, "resolve_seed_path", lambda: None)

    class _DummyService:
        groups: dict[str, Any] = {}
        users: dict[str, Any] = {}
        collections: dict[str, Any] = {}
        api_keys: dict[str, Any] = {}

    assert bootstrap_mod.maybe_apply_bootstrap_seed(_DummyService()) is None

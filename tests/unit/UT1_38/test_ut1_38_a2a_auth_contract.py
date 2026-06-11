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

import pytest

from index_server.auth.middleware import AuthMiddleware, flat_roles_for


def test_a2a_api_key_validation_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: FR-01B, FR-04
    monkeypatch.setenv("TEST_A2A_API_KEY", "12345678")
    auth = AuthMiddleware()

    via_header = auth.api_key_identity({"x-api-key": "12345678"})
    via_bearer = auth.api_key_identity({"authorization": "Bearer 12345678"})
    via_auth = auth.identity_from_headers({"authorization": "Bearer 12345678"})

    assert via_header.token_type == "api_key"
    assert via_bearer.token_type == "api_key"
    assert via_auth.token_type == "api_key"
    assert via_header.roles == via_bearer.roles == via_auth.roles
    assert "admin" in via_header.roles
    assert flat_roles_for(via_header.roles) == {"admin"}
    assert "*" in via_header.permissions


def test_a2a_api_key_invalid_rejected() -> None:
    auth = AuthMiddleware(api_keys={"12345678": {"admin"}})
    with pytest.raises(PermissionError):
        auth.api_key_identity({"authorization": "Bearer wrong"})


def test_api_key_env_mapping_parses_roles_and_skips_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_DOG__INDEX__AUTH__API_KEYS", " , scoped-key:read-only|read-write , bare-key ")
    monkeypatch.delenv("TEST_A2A_API_KEY", raising=False)

    auth = AuthMiddleware()
    scoped = auth.api_key_identity({"x-api-key": "scoped-key"})
    bare = auth.api_key_identity({"x-api-key": "bare-key"})

    assert scoped.roles == {"viewer", "user"}
    assert flat_roles_for(scoped.roles) == {"read-write"}
    assert {"collection.read", "collection.write"}.issubset(scoped.permissions)
    assert "admin" not in bare.roles
    assert "*" not in bare.permissions
    assert flat_roles_for(bare.roles) == {"read-only"}
    assert AuthMiddleware._default_roles() == set()


def test_role_specific_api_key_env_mapping_separates_rbac_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUD_DOG__INDEX__AUTH__API_KEYS", raising=False)
    monkeypatch.delenv("TEST_A2A_API_KEY", raising=False)
    monkeypatch.setenv("CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY", "admin-role-key")
    monkeypatch.setenv("CLOUD_DOG__INDEX__AUTH__WRITER_API_KEY", "writer-role-key")
    monkeypatch.setenv("CLOUD_DOG__INDEX__AUTH__READER_API_KEY", "reader-role-key")

    auth = AuthMiddleware()

    assert auth.api_key_identity({"x-api-key": "admin-role-key"}).roles == {"admin"}
    assert flat_roles_for(auth.api_key_identity({"x-api-key": "admin-role-key"}).roles) == {"admin"}
    assert "*" in auth.api_key_identity({"x-api-key": "admin-role-key"}).permissions
    assert auth.api_key_identity({"x-api-key": "writer-role-key"}).roles == {"user"}
    assert flat_roles_for(auth.api_key_identity({"x-api-key": "writer-role-key"}).roles) == {"read-write"}
    assert "collection.write" in auth.api_key_identity({"x-api-key": "writer-role-key"}).permissions
    assert auth.api_key_identity({"x-api-key": "reader-role-key"}).roles == {"viewer"}
    assert flat_roles_for(auth.api_key_identity({"x-api-key": "reader-role-key"}).roles) == {"read-only"}
    assert auth.api_key_identity({"x-api-key": "reader-role-key"}).permissions == {"collection.read"}


def test_auth_middleware_refreshes_provider_after_runtime_key_update() -> None:
    auth = AuthMiddleware(api_keys={"bootstrap-key": {"admin"}})
    auth.register_api_key("fresh-key", roles={"admin"})

    refreshed = auth.api_key_identity({"x-api-key": "fresh-key"})

    assert refreshed.token_type == "api_key"
    assert refreshed.roles == {"admin"}

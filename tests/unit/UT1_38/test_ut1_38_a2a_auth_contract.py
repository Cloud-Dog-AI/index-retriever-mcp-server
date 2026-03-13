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

# index-retriever-mcp-server — UT1.38
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: A2A auth contract parity with shared API-key authority.

from __future__ import annotations

import pytest

from index_server.auth.middleware import AuthMiddleware


def test_a2a_api_key_validation_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_A2A_API_KEY", "12345678")
    auth = AuthMiddleware()

    via_header = auth.authenticate_api_key({"x-api-key": "12345678"})
    via_bearer = auth.authenticate_api_key({"authorization": "Bearer 12345678"})
    via_auth = auth.authenticate({"authorization": "Bearer 12345678"})

    assert via_header.token_type == "api_key"
    assert via_bearer.token_type == "api_key"
    assert via_auth.token_type == "api_key"
    assert via_header.roles == via_bearer.roles == via_auth.roles


def test_a2a_api_key_invalid_rejected() -> None:
    auth = AuthMiddleware(api_keys={"12345678": {"admin"}})
    with pytest.raises(PermissionError):
        auth.authenticate_api_key({"authorization": "Bearer wrong"})


def test_api_key_env_mapping_parses_roles_and_skips_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_DOG__INDEX__AUTH__API_KEYS", " , scoped-key:reader|writer , bare-key ")
    monkeypatch.delenv("TEST_A2A_API_KEY", raising=False)

    auth = AuthMiddleware()
    scoped = auth.authenticate_api_key({"x-api-key": "scoped-key"})
    bare = auth.authenticate_api_key({"x-api-key": "bare-key"})

    assert scoped.roles == {"reader", "writer"}
    assert bare.roles == {"admin", "maintainer", "writer", "reader"}

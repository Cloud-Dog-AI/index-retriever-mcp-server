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

import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from tests.http_paths import a2a_health_path
from tests.live_runtime import LiveIndexRuntime
import pytest


def _http_status(url: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
    req = Request(url=url, headers=headers or {}, method="GET")
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_a2a_health_auth_matrix(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    valid_key = os.environ.get("TEST_A2A_API_KEY", "test-api-key").strip() or "test-api-key"

    if runtime_mode == "local-server":
        client = TestClient(build_api_app(service=live_service))
        no_auth = client.get(a2a_health_path())
        bad_auth = client.get(a2a_health_path(), headers={"Authorization": "Bearer wrong-key"})
        good_auth = client.get(a2a_health_path(), headers={"Authorization": f"Bearer {valid_key}"})

        assert no_auth.status_code == 401
        assert bad_auth.status_code == 401
        assert good_auth.status_code == 200
        assert good_auth.json().get("status") == "ok"
        return

    assert runtime_endpoints is not None
    base = runtime_endpoints["api_base_url"]

    no_auth_code, _ = _http_status(f"{base}{a2a_health_path()}")
    bad_auth_code, _ = _http_status(
        f"{base}{a2a_health_path()}",
        {"Authorization": "Bearer wrong-key"},
    )
    good_auth_code, good_auth_body = _http_status(
        f"{base}{a2a_health_path()}",
        {"Authorization": f"Bearer {valid_key}"},
    )

    assert no_auth_code == 401
    assert bad_auth_code == 401
    assert good_auth_code == 200, good_auth_body

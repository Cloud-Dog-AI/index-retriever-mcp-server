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

"""Playwright admin WebUI verification.

Description:
- Verifies that the in-repo Admin WebUI is a strict HTTP API client and can
  complete profile, user, group, and API-key administration in a browser.

Related requirements:
- FR-01, FR-17
- CFG-07, CFG-11, CFG-13

Related architecture:
- ARCHITECTURE.md WebUI/API topology
"""

from __future__ import annotations

import json
import socket
import threading
import time
from contextlib import closing
from typing import Any
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
import uvicorn

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService


class _UvicornThread:
    """Run the API app in a background thread for browser-driven tests."""

    def __init__(self, app: Any, host: str, port: int) -> None:
        self._config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
        self._server = uvicorn.Server(self._config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self) -> None:
        """Start the server thread and wait for `/health` to answer."""
        self._thread.start()
        deadline = time.time() + 30.0
        health_url = f"http://{self._config.host}:{self._config.port}/health"
        while time.time() < deadline:
            if self._server.started:
                try:
                    request = Request(health_url, method="GET")
                    with urlopen(request, timeout=2) as response:
                        if int(getattr(response, "status", 0) or 0) == 200:
                            return
                except OSError:
                    time.sleep(0.2)
                    continue
            time.sleep(0.1)
        raise RuntimeError(f"Timed out waiting for browser test server at {health_url}")

    def stop(self) -> None:
        """Signal shutdown and wait for the thread to exit."""
        self._server.should_exit = True
        self._thread.join(timeout=15.0)


def _free_port() -> int:
    """Allocate a free localhost TCP port."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def _fill_and_save_auth(page: Any, *, mode: str, token: str) -> None:
    """Set the WebUI auth mode and token, then persist it in the page."""
    page.locator('[data-testid="auth-mode"]').select_option(mode)
    page.locator('[data-testid="auth-token"]').fill(token)
    page.locator('[data-testid="auth-save"]').click()
    page.wait_for_function(
        """([testId, text]) => {
            const node = document.querySelector(`[data-testid="${testId}"]`);
            return node && node.textContent.includes(text);
        }""",
        arg=["auth-result", '"status": "saved"'],
    )


def _wait_result_contains(page: Any, test_id: str, text: str) -> None:
    """Wait until a result panel contains the expected text fragment."""
    page.wait_for_function(
        """([testId, expected]) => {
            const node = document.querySelector(`[data-testid="${testId}"]`);
            return node && node.textContent.includes(expected);
        }""",
        arg=[test_id, text],
    )


def test_admin_webui_profile_security_crud(
    tmp_path: Any,
) -> None:
    """Drive the admin WebUI through real HTTP requests with Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - enforced by runtime setup
        pytest.fail(f"Playwright is not installed in the active venv: {exc}")

    suffix = uuid4().hex[:8]
    profile_id = f"ui_profile_{suffix}"
    blocked_profile_id = f"ui_profile_blocked_{suffix}"
    user_id = f"ui_user_{suffix}"
    group_id = f"ui_group_{suffix}"
    api_key_label = f"ui_key_{suffix}"

    host = "127.0.0.1"
    port = _free_port()
    service = IndexService(audit_path=str(tmp_path / "admin-webui-audit.jsonl"))
    server = _UvicornThread(build_api_app(service=service), host, port)
    server.start()
    base_url = f"http://{host}:{port}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})

            page.goto(f"{base_url}/admin/ui/profiles", wait_until="networkidle")
            _fill_and_save_auth(page, mode="bearer", token="valid-admin-token")
            page.locator('[data-testid="health-refresh"]').click()
            _wait_result_contains(page, "health-result", '"status": "ok"')

            page.locator('[data-testid="profile-id"]').fill(profile_id)
            page.locator('[data-testid="profile-backend"]').fill("qdrant")
            page.locator('[data-testid="profile-roles"]').fill("reader,writer,maintainer")
            page.locator('[data-testid="profile-create"]').click()
            _wait_result_contains(page, "profiles-result", profile_id)
            _wait_result_contains(page, "profiles-table-body", profile_id)

            page.locator('[data-testid="profile-backend"]').fill("chroma")
            page.locator('[data-testid="profile-roles"]').fill("reader,writer")
            page.locator('[data-testid="profile-update"]').click()
            _wait_result_contains(page, "profiles-result", '"backend": "chroma"')

            page.goto(f"{base_url}/admin/ui/security", wait_until="networkidle")
            _fill_and_save_auth(page, mode="bearer", token="valid-admin-token")

            page.locator('[data-testid="user-id"]').fill(user_id)
            page.locator('[data-testid="user-display-name"]').fill("UI Operator")
            page.locator('[data-testid="user-roles"]').fill("admin")
            page.locator('[data-testid="user-create"]').click()
            _wait_result_contains(page, "users-result", user_id)
            _wait_result_contains(page, "users-table-body", user_id)

            page.locator('[data-testid="group-id"]').fill(group_id)
            page.locator('[data-testid="group-roles"]').fill("writer")
            page.locator('[data-testid="group-members"]').fill(user_id)
            page.locator('[data-testid="group-create"]').click()
            _wait_result_contains(page, "groups-result", group_id)
            _wait_result_contains(page, "groups-table-body", group_id)

            page.locator('[data-testid="api-key-label"]').fill(api_key_label)
            page.locator('[data-testid="api-key-user-id"]').fill(user_id)
            page.locator('[data-testid="api-key-roles"]').fill("admin")
            page.locator('[data-testid="api-key-capabilities"]').fill("admin,search,ingest")
            page.locator('[data-testid="api-key-create"]').click()
            _wait_result_contains(page, "api-keys-result", api_key_label)

            api_key_payload = json.loads(page.locator('[data-testid="api-keys-result"]').text_content() or "{}")
            api_key_record = api_key_payload["api_key"]
            issued_key_id = str(api_key_record["key_id"])
            issued_token = str(api_key_record["token"])
            assert issued_key_id
            assert issued_token
            _wait_result_contains(page, "api-key-token", issued_token)

            _fill_and_save_auth(page, mode="api-key", token=issued_token)
            page.locator('[data-testid="events-refresh"]').click()
            _wait_result_contains(page, "events-result", '"entity_type": "api_key"')

            page.goto(f"{base_url}/admin/ui/profiles", wait_until="networkidle")
            _fill_and_save_auth(page, mode="bearer", token="valid-reader-token")
            page.locator('[data-testid="profile-id"]').fill(blocked_profile_id)
            page.locator('[data-testid="profile-backend"]').fill("qdrant")
            page.locator('[data-testid="profile-roles"]').fill("reader")
            page.locator('[data-testid="profile-create"]').click()
            _wait_result_contains(page, "profiles-result", '"status": 403')

            _fill_and_save_auth(page, mode="bearer", token="valid-admin-token")
            page.locator('[data-testid="profile-id"]').fill(profile_id)
            page.locator('[data-testid="profile-delete"]').click()
            _wait_result_contains(page, "profiles-result", '"status": "ok"')

            page.goto(f"{base_url}/admin/ui/security", wait_until="networkidle")
            _fill_and_save_auth(page, mode="bearer", token="valid-admin-token")
            page.locator('[data-testid="api-key-id"]').fill(issued_key_id)
            page.locator('[data-testid="api-key-revoke"]').click()
            _wait_result_contains(page, "api-keys-result", '"revoked": true')

            page.locator('[data-testid="group-id"]').fill(group_id)
            page.locator('[data-testid="group-delete"]').click()
            _wait_result_contains(page, "groups-result", '"status": "ok"')

            page.locator('[data-testid="user-id"]').fill(user_id)
            page.locator('[data-testid="user-delete"]').click()
            _wait_result_contains(page, "users-result", '"status": "ok"')

            browser.close()
    finally:
        server.stop()

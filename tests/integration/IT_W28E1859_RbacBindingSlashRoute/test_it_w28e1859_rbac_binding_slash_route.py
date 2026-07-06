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
#
# Description: W28E-1859 ST-6 regression — the shipped @cloud-dog/idam WebUI
#   (IdamRbacPage) creates an RBAC binding by POSTing to the canonical SLASH
#   route `/<prefix>/idam/v1/rbac/bindings` with a `subject_id` payload. Before
#   this lane the backend only registered the HYPHEN alias `rbac-bindings` and
#   the create handler only read `subject`/`entity_id`, so the WebUI POST hit
#   405/400 and the "Created binding" toast never appeared (SecurityAdmin AT
#   failure). This test locks the slash-route + subject_id contract.
# Related requirements: FR-004, FR-018
# Related tests: AT_WEBUI_SecurityAdmin

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from index_server import api_server
from index_tools.tools.service import IndexService

_ADMIN = {"x-api-key": "valid-admin-token"}


def _build_app_like_runtime(service: IndexService):
    """Build the API app exactly like the deployed dev-tier runtime.

    The production runtime boots as a standalone process without
    ``PYTEST_CURRENT_TEST`` set (index-retriever ST-6, commit 43d4a15 strips it
    from the WebUI runtime subprocess env). Building in-process under pytest with
    that marker present forces the timeout-middleware materialisation down its
    "in pytest" branch and the later @app.middleware("http") registration then
    raises "Cannot add middleware after an application has started" — a boot-path
    artefact unrelated to the RBAC route contract under test. Strip the marker for
    the duration of the build so this test exercises the deployed route table.
    """
    saved = os.environ.pop("PYTEST_CURRENT_TEST", None)
    try:
        return api_server.build_api_app(service=service)
    finally:
        if saved is not None:
            os.environ["PYTEST_CURRENT_TEST"] = saved


@pytest.mark.IT
@pytest.mark.webui
@pytest.mark.req("FR-004")
@pytest.mark.req("FR-018")
@pytest.mark.parametrize("prefix", ["/v1", "/api/v1"])
def test_webui_slash_rbac_binding_create_accepts_subject_id(
    service: IndexService, prefix: str
) -> None:
    """POST /<prefix>/idam/v1/rbac/bindings with the WebUI subject_id payload succeeds."""
    app = _build_app_like_runtime(service)
    client = TestClient(app)

    group_id = f"w28e1859-{prefix.strip('/').replace('/', '-')}-grp"
    created = client.post(
        f"{prefix}/admin/groups",
        json={"name": group_id, "description": "W28E-1859 regression group"},
        headers=_ADMIN,
    )
    assert created.status_code == 200, created.text

    # Exact payload shape emitted by @cloud-dog/idam rbacBindingPayload(): subject_id,
    # resource_id, project — via the canonical SLASH route the WebUI calls.
    resp = client.post(
        f"{prefix}/idam/v1/rbac/bindings",
        json={
            "subject_type": "group",
            "subject_id": group_id,
            "resource_type": "system",
            "resource_id": "system",
            "permission": "read",
            "project": "platform",
        },
        headers=_ADMIN,
    )
    assert resp.status_code in (200, 201), (
        f"WebUI slash rbac/bindings POST must succeed, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    binding = body.get("binding", body)
    # subject echoed back proves the subject_id spelling was honoured (not dropped -> 400).
    assert group_id in str(binding), f"created binding does not reference subject: {body}"

    # And the slash LIST route returns the new binding (WebUI refresh path).
    listed = client.get(f"{prefix}/idam/v1/rbac/bindings", headers=_ADMIN)
    assert listed.status_code == 200, listed.text
    assert group_id in listed.text

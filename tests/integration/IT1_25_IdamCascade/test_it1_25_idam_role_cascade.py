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

# W28E-1805B (index-retriever Stream-B) — D5 IDAM-uplift integration.
# Promotes the W28A-749 cascade smoke (tests/smoke/cascade_smoke.py) into the IT tier and
# adds the PS-IDAM-ROLE-CASCADE baseline/overlay proof, so the six undeletable baseline roles,
# the role_overlay= baseline merge, the scoped RBACBinding cascade, and the live revoke
# (no restart) are all exercised on the deployed code path under the IT gate.
"""IT1.25 — PS-IDAM-ROLE-CASCADE conformance (FR-008).

Two contracts:
  * baseline + overlay merge — the composed cloud_dog_idam RBAC engine carries the PS-82 §7.2
    undeletable baseline roles AND the index-retriever overlay permissions merged on top
    (role_overlay=, not role_permissions= replace).
  * group→collection cascade with live revoke — a ``restricted`` principal (no flat
    collection.read) gains scoped read on collection C only via the group→collection RBAC
    binding, is denied on the unbound collection D (scoped) and on write (graded), and is
    revoked the instant the group membership edge is removed — same process, no restart.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_server.auth import cascade
from index_server.auth.middleware import INDEX_ROLE_PERMISSIONS, AuthMiddleware
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path

# PS-82 §7.2 undeletable baseline roles that role_overlay= must preserve (not replace).
PS82_BASELINE_ROLES = {"admin", "user", "viewer", "audit-log", "group-admin", "job-control"}

ADMIN = "valid-admin-token"
GU_TOKEN = "it125-groupuser-token"
GU_KEY = "it125-gukey"
GU_PRINCIPAL = f"apikey:{GU_KEY}"
PROFILE = "default"
COL_C = "it125-cascade-c"
COL_D = "it125-cascade-d"
GROUP = "It125Gcascade"


def _role_permission_map(engine: object) -> dict[str, set[str]]:
    """Best-effort public/inner read of the composed role→permission map."""
    for attr in ("role_permissions", "_role_permissions"):
        value = getattr(engine, attr, None)
        if isinstance(value, dict):
            return {str(k): set(v) for k, v in value.items()}
    raise AssertionError("RBAC engine exposes no role→permission map")


def _post(
    client: TestClient, tool: str, payload: dict[str, object], token: str
) -> tuple[int, dict[str, object]]:
    response = client.post(
        api_tools_path(tool), json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        body = response.json()
    except Exception:  # pragma: no cover — defensive
        body = {"_raw": response.text}
    return response.status_code, body


@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-008")
def test_it1_25_baseline_roles_and_overlay_merge() -> None:
    """role_overlay= composes the six PS-82 baseline roles with the index-retriever overlay."""
    middleware = AuthMiddleware(api_keys=None)
    role_perms = _role_permission_map(middleware._rbac)
    roles = set(role_perms)

    missing = PS82_BASELINE_ROLES - roles
    assert not missing, (
        f"role_overlay= must preserve the PS-82 §7.2 baseline; missing={sorted(missing)} "
        f"(present={sorted(roles)}). A replace (role_permissions=) would drop these."
    )
    # Overlay merged on top of the baseline (not replacing it).
    assert "*" in role_perms["admin"], role_perms["admin"]
    for permission in INDEX_ROLE_PERMISSIONS["user"]:
        assert permission in role_perms["user"], (permission, role_perms["user"])
    assert "collection.read" in role_perms["viewer"], role_perms["viewer"]


@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.negative
@pytest.mark.req("FR-008")
def test_it1_25_group_collection_cascade_live_revoke(service: IndexService) -> None:
    """group-admin binds G→C; add U→G grants scoped read live; remove U→G revokes it live."""
    assert cascade.CASCADE_AVAILABLE, "cloud_dog_idam>=0.5.x resolver/guard required for the cascade"
    client = TestClient(build_api_app(service=service))

    # setup as admin: a restricted principal with NO flat collection.read
    status, body = _post(
        client,
        "admin_api_key_create",
        {"key_id": GU_KEY, "token": GU_TOKEN, "roles": ["restricted"], "label": "it125-groupuser"},
        ADMIN,
    )
    assert status == 200, body
    for collection in (COL_C, COL_D):
        status, body = _post(
            client, "admin_collection_create", {"profile": PROFILE, "collection": collection}, ADMIN
        )
        assert status == 200, (collection, body)
    status, body = _post(client, "admin_group_create", {"group_id": GROUP, "members": []}, ADMIN)
    assert status == 200, body
    status, body = _post(
        client,
        "admin_rbac_bind",
        {
            "entity_type": "group",
            "entity_id": GROUP,
            "resource_type": "collection",
            "resource_id": f"{PROFILE}:{COL_C}",
            "permission": "collection.read",
        },
        ADMIN,
    )
    assert status == 200, body
    assert body["binding"]["resource_id"] == f"{PROFILE}:{COL_C}", body

    # STEP 1 — not in G → read C denied (default-deny, non-vacuous cascade)
    status, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_C}, GU_TOKEN)
    assert status == 403, f"STEP1 baseline: restricted (not in G) read C must be 403, got {status}"

    # STEP 2 — group-admin adds U to G
    status, body = _post(
        client, "admin_group_update", {"group_id": GROUP, "members": [GU_PRINCIPAL]}, ADMIN
    )
    assert status == 200, body

    # STEP 3 — cascade ON, live, no restart: scoped + graded
    status, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_C}, GU_TOKEN)
    assert status == 200, f"STEP3 cascade-on: read C must be 200 via binding, got {status}"
    status, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_D}, GU_TOKEN)
    assert status == 403, f"STEP3 scoped: read D (unbound) must be 403, got {status}"
    status, _ = _post(
        client,
        "ingest_text",
        {"profile": PROFILE, "collection": COL_C, "text": "x", "source": "file://c/x.txt"},
        GU_TOKEN,
    )
    assert status == 403, f"STEP3 graded: write C (only read bound) must be 403, got {status}"

    # STEP 4 — group-admin removes U from G
    status, body = _post(client, "admin_group_update", {"group_id": GROUP, "members": []}, ADMIN)
    assert status == 200, body

    # STEP 5 — cascade OFF, live revoke, no restart
    status, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_C}, GU_TOKEN)
    assert status == 403, f"STEP5 revoke: read C after removal must be 403, got {status}"

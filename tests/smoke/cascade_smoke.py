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

# W28A-749 (IDAM Thread-b) — T3-IR-CASCADE: group→collection resource-scoped cascade (IDAM-B2 §4.3).
"""T3-IR-CASCADE — the W28A-741 keystone cascade, proven live in-process on the deployed code path.

Requires the cloud_dog_idam 0.5.x resolver/guard (``cascade.CASCADE_AVAILABLE``); the lane pins
``cloud_dog_idam>=0.5.1`` so this runs (it is NOT conditionally skipped). The principal is a
``restricted`` api-key (no flat ``collection.read``) — access to collection C comes ONLY via the
group→collection RBAC binding, so the cascade is non-vacuous.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_server.auth import cascade
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path

ADMIN = "valid-admin-token"
GU_TOKEN = "groupuser-cascade-token"
GU_KEY = "gukey-cascade"
GU_PRINCIPAL = f"apikey:{GU_KEY}"
PROFILE = "default"
COL_C = "cascade-c"
COL_D = "cascade-d"
GROUP = "Gcascade"


def _post(client, tool, payload, token):
    r = client.post(api_tools_path(tool), json=payload, headers={"Authorization": f"Bearer {token}"})
    try:
        body = r.json()
    except Exception:
        body = {"_raw": r.text}
    return r.status_code, body


def test_t3_ir_cascade(service: IndexService) -> None:
    """group-admin binds G→collection C; add U to G → U reads C only; remove U → revoked (live)."""
    assert cascade.CASCADE_AVAILABLE, "cloud_dog_idam>=0.5.x resolver/guard required for T3-IR-CASCADE"
    client = TestClient(build_api_app(service=service))

    # --- setup (as admin) ---
    s, b = _post(client, "admin_api_key_create",
                 {"key_id": GU_KEY, "token": GU_TOKEN, "roles": ["restricted"], "label": "groupuser"}, ADMIN)
    assert s == 200, b  # token supplied by us (GU_TOKEN); response masks the secret
    for col in (COL_C, COL_D):
        s, b = _post(client, "admin_collection_create", {"profile": PROFILE, "collection": col}, ADMIN)
        assert s == 200, (col, b)
    s, b = _post(client, "admin_group_create", {"group_id": GROUP, "members": []}, ADMIN)
    assert s == 200, b
    # bind group G -> collection C = collection.read (the cascade edge; no bespoke FK)
    s, b = _post(client, "admin_rbac_bind",
                 {"entity_type": "group", "entity_id": GROUP, "resource_type": "collection",
                  "resource_id": f"{PROFILE}:{COL_C}", "permission": "collection.read"}, ADMIN)
    assert s == 200, b
    assert b["binding"]["resource_id"] == f"{PROFILE}:{COL_C}", b

    # --- STEP 1: U not in G -> read C denied (default-DENY, no membership/binding) ---
    s, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_C}, GU_TOKEN)
    assert s == 403, f"STEP1 baseline: GROUPUSER (not in G) read C must be 403, got {s}"

    # --- STEP 2: group-admin adds U to G ---
    s, b = _post(client, "admin_group_update",
                 {"group_id": GROUP, "members": [GU_PRINCIPAL]}, ADMIN)
    assert s == 200, b

    # --- STEP 3: cascade ON (live, no restart) ---
    s, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_C}, GU_TOKEN)
    assert s == 200, f"STEP3 cascade-on: GROUPUSER read C must be 200 via binding, got {s}"
    s, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_D}, GU_TOKEN)
    assert s == 403, f"STEP3 scoped: GROUPUSER read D (not bound) must be 403, got {s}"
    s, _ = _post(client, "ingest_text",
                 {"profile": PROFILE, "collection": COL_C, "text": "x", "source": "file://c/x.txt"}, GU_TOKEN)
    assert s == 403, f"STEP3 graded: GROUPUSER write C (only read bound) must be 403, got {s}"

    # --- STEP 4: group-admin removes U from G ---
    s, b = _post(client, "admin_group_update",
                 {"group_id": GROUP, "members": []}, ADMIN)
    assert s == 200, b

    # --- STEP 5: cascade OFF (membership gone → revoked, live, no restart) ---
    s, _ = _post(client, "collection_get", {"profile": PROFILE, "collection": COL_C}, GU_TOKEN)
    assert s == 403, f"STEP5 revoke: GROUPUSER read C after removal must be 403, got {s}"

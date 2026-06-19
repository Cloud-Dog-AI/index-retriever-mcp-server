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

# W28A-749 (IDAM Thread-b) — access-control matrix T0/T1/T2 smoke (ROLES-AND-USECASES.md §3).
"""T0/T1/T2 IDAM smoke — the cloud_dog_idam-0.4.x-independent rows of the b-4 matrix.

These tests exercise the REAL auth path (cloud_dog_idam RBACEngine + AuthMiddleware) in-process via
``TestClient`` against ``build_api_app`` / ``build_mcp_app`` / ``build_a2a_app`` — the established harness
(cf. tests/integration/IT1_21). They assert role-by-surface behaviour that does NOT depend on the W28A-741
resource-aware resolver/guard (cloud_dog_idam 0.5.0). The 0.5.0-gated rows — T2-IR-NOSECRET (central
masking), T3-IR-CASCADE (group→collection cascade), the no-unguarded-route guard_registry meta-test — are
added in the keystone pass once ``cloud-dog-idam==0.5.0`` resolves from the normal internal index, so no
test here is conditionally skipped.

Canonical non-secret test tokens (defined in every tests/env-* CLOUD_DOG__INDEX__AUTH__API_KEYS contract;
matches IT1_21): admin=``valid-admin-token``, writer/user=``valid-writer-token``, reader/viewer=
``valid-reader-token``, strict-local A2A=``12345678``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_server.mcp_server import build_mcp_app
from index_tools.tools.registry import build_default_tool_registry
from index_tools.tools.service import IndexService
from tests.http_paths import api_base_path, api_tools_path, a2a_health_path, mcp_tools_path

ADMIN = "valid-admin-token"
WRITER = "valid-writer-token"
READER = "valid-reader-token"
A2A_LOCAL = "12345678"

EXPECTED_TOOL_COUNT = 94  # FR-16A; UT1_40 asserts the same runtime value


def _hdr(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _post(client: TestClient, path: str, payload: dict, token: str | None):
    r = client.post(path, json=payload, headers=_hdr(token))
    try:
        body = r.json()
    except Exception:
        body = {"_raw": r.text}
    return r.status_code, body


# --- T0 smoke -------------------------------------------------------------------
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-16A")
def test_t0_ir_tools_count_runtime_94(service: IndexService) -> None:
    """T0-IR-TOOLS-COUNT: runtime registry == 94, unique (reconciles FR-16A docs)."""
    reg = build_default_tool_registry()
    tools = reg.list_tools()
    names = [t["name"] if isinstance(t, dict) else t.name for t in tools]
    assert len(names) == EXPECTED_TOOL_COUNT, f"runtime tool count {len(names)} != {EXPECTED_TOOL_COUNT}"
    assert len(set(names)) == EXPECTED_TOOL_COUNT, "duplicate tool names in registry"


def test_t0_ir_health_public(service: IndexService) -> None:
    """T0-IR-LIFECYCLE: /health is public (no auth) and 200."""
    client = TestClient(build_api_app(service=service))
    r = client.get(f"{api_base_path()}/health")
    assert r.status_code == 200, r.text


# --- T1 common-IDAM -------------------------------------------------------------
def test_t1_ir_auth_401_api_anon(service: IndexService) -> None:
    """T1-IR-AUTH-401 (API): anon → 401 on a gated tool; never materialised to admin."""
    client = TestClient(build_api_app(service=service))
    status, body = _post(client, api_tools_path("profiles_list"), {}, None)
    assert status == 401, f"anon API tool call must be 401, got {status}: {body}"


def test_t1_ir_auth_401_mcp_anon(service: IndexService) -> None:
    """T1-IR-AUTH-401 (MCP): anon → 401 on a gated MCP tool."""
    client = TestClient(build_mcp_app(service=service))
    status, body = _post(client, mcp_tools_path("profiles_list"), {}, None)
    assert status == 401, f"anon MCP tool call must be 401, got {status}: {body}"


def test_t1_ir_auth_me_401_anon(service: IndexService) -> None:
    """T1-IR-AUTH-401 (/auth/me): anon → 401."""
    client = TestClient(build_api_app(service=service))
    r = client.get("/auth/me")
    assert r.status_code == 401, f"/auth/me anon must be 401, got {r.status_code}"


def test_t1_ir_a2a_401_then_strict_local_200(service: IndexService) -> None:
    """T1-IR-A2A-401 (FR-01B): /a2a/health no-auth → 401; Bearer 12345678 → 200 strict-local."""
    client = TestClient(build_api_app(service=service))
    r_anon = client.get(a2a_health_path())
    assert r_anon.status_code == 401, f"/a2a/health anon must be 401, got {r_anon.status_code}"
    r_ok = client.get(a2a_health_path(), headers=_hdr(A2A_LOCAL))
    assert r_ok.status_code == 200, f"/a2a/health Bearer 12345678 must be 200, got {r_ok.status_code}"


# --- T2 RBAC-by-role ------------------------------------------------------------
def test_t2_ir_adminonly_profile_create(service: IndexService) -> None:
    """T2-IR-ADMINONLY: non-admin → 403 on admin tool; admin → 200 (FR-05/FR-16)."""
    client = TestClient(build_api_app(service=service))
    payload = {"profile": "t2_adminonly", "backend": "memory"}
    status_reader, body_reader = _post(client, api_tools_path("admin_profile_create"), payload, READER)
    assert status_reader == 403, f"reader admin_profile_create must be 403, got {status_reader}: {body_reader}"
    status_admin, body_admin = _post(client, api_tools_path("admin_profile_create"), payload, ADMIN)
    assert status_admin == 200, f"admin admin_profile_create must be 200, got {status_admin}: {body_admin}"


def test_t2_ir_collection_rbac_write_graded(service: IndexService) -> None:
    """T2-IR-COLLECTION-RBAC: reader → 403 on write (ingest); writer → allowed (extends IT1_21)."""
    client = TestClient(build_api_app(service=service))
    ing = {"profile": "default", "collection": "t2_rbac", "text": "x", "source": "file://t2/x.txt"}
    status_reader, body_reader = _post(client, api_tools_path("ingest_text"), ing, READER)
    assert status_reader == 403, f"reader ingest_text must be 403, got {status_reader}: {body_reader}"
    status_writer, body_writer = _post(client, api_tools_path("ingest_text"), ing, WRITER)
    assert status_writer in (200, 202), f"writer ingest_text must be allowed, got {status_writer}: {body_writer}"


def test_t2_ir_service_scope_read_vs_write(service: IndexService) -> None:
    """T2-IR-SERVICE-SCOPE: viewer key reads (200) but cannot write (403)."""
    client = TestClient(build_api_app(service=service))
    status_read, _ = _post(client, api_tools_path("profiles_list"), {}, READER)
    assert status_read == 200, f"reader profiles_list must be 200, got {status_read}"
    status_write, body_write = _post(
        client, api_tools_path("admin_collection_create"),
        {"profile": "default", "collection": "t2_scope"}, READER,
    )
    assert status_write == 403, f"reader admin_collection_create must be 403, got {status_write}: {body_write}"

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

"""W28E-603 Phase 1 transport tests: the basic CRUD API and basic MCP list/get tools
(design brief §12, §13, §24 Phase 1). Proves real execution end-to-end through the
authenticated FastAPI app and the MCP tools endpoint — not mere registration (§13)."""


from __future__ import annotations
import pytest

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path

_ADMIN = {"Authorization": "Bearer valid-admin-token"}
_READER = {"Authorization": "Bearer valid-reader-token"}

_DOC = {
    "document": {
        "profile_id": "default",
        "collection_id": "it_w28e603",
        "source_hash": "it-w28e603-rest",
        "source_filename": "spec.pdf",
        "extractor_provider": "manual",
    },
    "pages": [{"page_number": 1}, {"page_number": 2}],
    "sections": [
        {"section_id": "r", "title": "Introduction", "level": 0, "numbering_label": "1"},
        {"section_id": "c", "title": "Scope", "level": 1, "numbering_label": "1.1", "parent_section_id": "r"},
    ],
    "blocks": [{"text": "body", "reading_order_index": 0, "block_type": "paragraph"}],
}
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_structure_rest_crud_lifecycle(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))

    # health
    health = client.get("/api/v1/structure/health", headers=_ADMIN)
    assert health.status_code == 200, health.text
    assert health.json()["component"] == "structure"

    # create
    created = client.post("/api/v1/structure/documents", json=_DOC, headers=_ADMIN)
    assert created.status_code == 200, created.text
    sdid = created.json()["document"]["structure_document_id"]
    assert created.json()["document"]["page_count"] == 2

    # list (filtered by collection)
    listed = client.get(
        "/api/v1/structure/documents", params={"collection": "it_w28e603"}, headers=_ADMIN
    )
    assert listed.status_code == 200
    assert any(d["structure_document_id"] == sdid for d in listed.json()["documents"])

    # get with child include
    got = client.get(f"/api/v1/structure/documents/{sdid}", headers=_ADMIN)
    assert got.status_code == 200
    assert len(got.json()["pages"]) == 2 and len(got.json()["sections"]) == 2

    # outline tree
    outline = client.get(f"/api/v1/structure/documents/{sdid}/outline", headers=_ADMIN)
    assert outline.status_code == 200
    roots = outline.json()["outline"]
    assert len(roots) == 1 and roots[0]["children"][0]["title"] == "Scope"

    # pages + sections
    pages = client.get(f"/api/v1/structure/documents/{sdid}/pages", headers=_ADMIN)
    assert pages.status_code == 200 and pages.json()["count"] == 2
    sections = client.get(f"/api/v1/structure/documents/{sdid}/sections", headers=_ADMIN)
    assert sections.status_code == 200 and sections.json()["count"] == 2

    # delete + 404 afterwards
    deleted = client.delete(f"/api/v1/structure/documents/{sdid}", headers=_ADMIN)
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True
    missing = client.get(f"/api/v1/structure/documents/{sdid}", headers=_ADMIN)
    assert missing.status_code == 404
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_structure_rest_requires_write_permission(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    # reader may not create
    resp = client.post("/api/v1/structure/documents", json=_DOC, headers=_READER)
    assert resp.status_code == 403
    # reader may read the (empty) listing
    listing = client.get("/api/v1/structure/documents", headers=_READER)
    assert listing.status_code == 200
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_structure_mcp_tools_call_real_execution(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    payload = {
        "bundle": {
            "document": {
                "profile_id": "default",
                "collection_id": "it_w28e603_mcp",
                "source_hash": "it-w28e603-mcp",
                "extractor_provider": "manual",
            },
            "pages": [{"page_number": 1}],
        },
        "actor": "it-mcp",
    }
    created = client.post(api_tools_path("structure_document_create"), json=payload, headers=_ADMIN)
    assert created.status_code == 200, created.text
    sdid = created.json()["document"]["structure_document_id"]

    got = client.post(
        api_tools_path("structure_document_get"), json={"structure_document_id": sdid}, headers=_ADMIN
    )
    assert got.status_code == 200 and got.json()["document"]["structure_document_id"] == sdid

    listed = client.post(
        api_tools_path("structure_document_list"), json={"collection": "it_w28e603_mcp"}, headers=_ADMIN
    )
    assert listed.status_code == 200 and listed.json()["total"] >= 1

    deleted = client.post(
        api_tools_path("structure_document_delete"), json={"structure_document_id": sdid}, headers=_ADMIN
    )
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_structure_family_in_tools_list(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    resp = client.get(api_tools_path(), headers=_ADMIN)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    tools = body["tools"] if isinstance(body, dict) else body
    names = {tool["name"] for tool in tools}
    expected = {
        "structure_health",
        "structure_document_create",
        "structure_document_get",
        "structure_document_list",
        "structure_document_delete",
        "structure_outline_get",
        "structure_pages_list",
        "structure_sections_list",
    }
    assert expected <= names, f"missing structure tools: {sorted(expected - names)}"

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

"""W28E-603 Phases 2-5 transport tests: extraction + corpus + templates over MCP tools/call and REST
(design brief §12/§13; §25 #2/#3/#8/#9/#10). Real authenticated execution, offline (internal provider)."""


from __future__ import annotations
import pytest

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path

_ADMIN = {"Authorization": "Bearer valid-admin-token"}
_READER = {"Authorization": "Bearer valid-reader-token"}

_DOC1 = "# Introduction\nIntro.\n\n# Scope\nScope.\n"
_DOC2 = "# Introduction\nIntro two.\n\n# Scope\nScope two.\n"


def _extract(client, text, fname):
    r = client.post(api_tools_path("structure_extract"),
                    json={"text": text, "profile": "default", "collection": "it_p25", "source_filename": fname}, headers=_ADMIN)
    assert r.status_code == 200, r.text
    return r.json()["document"]["structure_document_id"]
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_phase25_mcp_extract_corpus_template(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    id1 = _extract(client, _DOC1, "d1.md")
    id2 = _extract(client, _DOC2, "d2.md")

    corp = client.post(api_tools_path("structure_corpus_create"),
                       json={"corpus": {"name": "it specs", "profile_id": "default", "collection_id": "it_p25", "document_ids": [id1, id2]}}, headers=_ADMIN)
    assert corp.status_code == 200, corp.text
    cid = corp.json()["corpus_id"]

    listed = client.post(api_tools_path("structure_corpus_list"), json={"profile": "default"}, headers=_ADMIN)
    assert listed.status_code == 200 and any(c["corpus_id"] == cid for c in listed.json()["corpora"])

    analysed = client.post(api_tools_path("structure_corpus_analyse"), json={"corpus_id": cid}, headers=_ADMIN)
    assert analysed.status_code == 200, analysed.text
    assert analysed.json()["dominant_section_sequence"] == ["introduction", "scope"]

    patterns = client.post(api_tools_path("structure_corpus_patterns_get"), json={"corpus_id": cid, "pattern_type": "section"}, headers=_ADMIN)
    assert patterns.status_code == 200 and patterns.json()["count"] == 1

    tmpl = client.post(api_tools_path("structure_template_generate"), json={"corpus_id": cid, "name": "IT Template"}, headers=_ADMIN)
    assert tmpl.status_code == 200, tmpl.text
    tid = tmpl.json()["template_id"]
    assert len(tmpl.json()["sections"]) == 2

    exported = client.post(api_tools_path("structure_template_export"), json={"template_id": tid, "format": "markdown"}, headers=_ADMIN)
    assert exported.status_code == 200 and "Section blueprint" in exported.json()["content"]

    deleted = client.post(api_tools_path("structure_template_delete"), json={"template_id": tid}, headers=_ADMIN)
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_phase25_rest_surface(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    # extract via REST
    e1 = client.post("/api/v1/structure/extract", json={"text": _DOC1, "profile": "default", "collection": "it_p25r", "source_filename": "r1.md"}, headers=_ADMIN)
    e2 = client.post("/api/v1/structure/extract", json={"text": _DOC2, "profile": "default", "collection": "it_p25r", "source_filename": "r2.md"}, headers=_ADMIN)
    assert e1.status_code == 200 and e2.status_code == 200, (e1.text, e2.text)
    ids = [e1.json()["document"]["structure_document_id"], e2.json()["document"]["structure_document_id"]]

    corp = client.post("/api/v1/structure/corpora", json={"name": "rest specs", "profile_id": "default", "collection_id": "it_p25r", "document_ids": ids}, headers=_ADMIN)
    assert corp.status_code == 200, corp.text
    cid = corp.json()["corpus_id"]

    assert client.get(f"/api/v1/structure/corpora/{cid}", headers=_ADMIN).status_code == 200
    assert client.get("/api/v1/structure/corpora", params={"profile": "default"}, headers=_ADMIN).status_code == 200

    analysed = client.post(f"/api/v1/structure/corpora/{cid}/analyse", headers=_ADMIN)
    assert analysed.status_code == 200 and analysed.json()["pattern_count"] >= 1

    pats = client.get(f"/api/v1/structure/corpora/{cid}/patterns", params={"pattern_type": "section"}, headers=_ADMIN)
    assert pats.status_code == 200 and pats.json()["count"] == 1

    tmpl = client.post("/api/v1/structure/templates", json={"corpus_id": cid, "name": "Rest Template"}, headers=_ADMIN)
    assert tmpl.status_code == 200, tmpl.text
    tid = tmpl.json()["template_id"]

    assert client.get(f"/api/v1/structure/templates/{tid}", headers=_ADMIN).status_code == 200
    assert client.get("/api/v1/structure/templates", params={"corpus_id": cid}, headers=_ADMIN).status_code == 200
    exp_md = client.get(f"/api/v1/structure/templates/{tid}/export", params={"format": "markdown"}, headers=_ADMIN)
    exp_js = client.get(f"/api/v1/structure/templates/{tid}/export", params={"format": "json"}, headers=_ADMIN)
    assert exp_md.status_code == 200 and exp_md.json()["format"] == "markdown"
    assert exp_js.status_code == 200 and exp_js.json()["format"] == "json"

    reader_delete = client.delete(f"/api/v1/structure/templates/{tid}", headers=_READER)
    assert reader_delete.status_code == 403
    deleted = client.delete(f"/api/v1/structure/templates/{tid}", headers=_ADMIN)
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True
    assert client.get(f"/api/v1/structure/templates/{tid}", headers=_ADMIN).status_code == 404

    # delete corpus
    assert client.delete(f"/api/v1/structure/corpora/{cid}", headers=_ADMIN).status_code == 200
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_phase25_rbac_reader_cannot_write(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    assert client.post("/api/v1/structure/extract", json={"text": _DOC1, "profile": "default", "collection": "x"}, headers=_READER).status_code == 403
    assert client.post("/api/v1/structure/corpora", json={"name": "n", "profile_id": "default"}, headers=_READER).status_code == 403
    assert client.get("/api/v1/structure/corpora", headers=_READER).status_code == 200


@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_phase25_openapi_includes_structure_routes(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, resp.text
    paths = resp.json()["paths"]
    expected = {
        "/api/v1/structure/health",
        "/api/v1/structure/documents",
        "/api/v1/structure/extract",
        "/api/v1/structure/corpora",
        "/api/v1/structure/corpora/{corpus_id}/analyse",
        "/api/v1/structure/templates",
        "/api/v1/structure/templates/{template_id}",
        "/api/v1/structure/templates/{template_id}/export",
    }
    assert expected <= set(paths), f"missing OpenAPI structure paths: {sorted(expected - set(paths))}"
    assert "delete" in paths["/api/v1/structure/templates/{template_id}"]
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_phase25_vdb_linkage(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    sdid = _extract(client, _DOC1, "lk.md")
    # MCP link
    r = client.post(api_tools_path("structure_link_to_vdb_records"),
                    json={"structure_document_id": sdid, "vdb_record_ids": ["r2", "r1"], "chunk_ids": ["c1"], "source_document_id": "src-1"}, headers=_ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["vdb_record_ids"] == ["r1", "r2"]
    assert r.json()["source_document_id"] == "src-1"
    # REST link + verify persisted
    r2 = client.post(f"/api/v1/structure/documents/{sdid}/vdb-links", json={"vdb_record_ids": ["r3"], "chunk_ids": ["c2", "c3"]}, headers=_ADMIN)
    assert r2.status_code == 200 and r2.json()["chunk_ids"] == ["c2", "c3"]
    got = client.get(f"/api/v1/structure/documents/{sdid}", headers=_ADMIN)
    assert got.json()["document"]["vdb_record_ids"] == ["r3"]

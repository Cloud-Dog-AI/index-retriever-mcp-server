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

"""W28E-1805B integration test: structure_extract -> corpus_analyse (distance/commonality)
-> template_generate -> template_match through the authenticated API (design brief §12/§13;
§25 #2/#3/#8/#9/#10). Real authenticated execution, offline internal provider."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path

_ADMIN = {"Authorization": "Bearer valid-admin-token"}
_READER = {"Authorization": "Bearer valid-reader-token"}

_DOC1 = "# Introduction\nWell formed English introduction paragraph here.\n\n# Scope\nScope text describing boundaries.\n"
_DOC2 = "# Introduction\nIntro two with English content.\n\n# Scope\nScope two text body.\n"


def _extract(client, text, fname, collection):
    r = client.post(
        api_tools_path("structure_extract"),
        json={"text": text, "profile": "default", "collection": collection, "source_filename": fname},
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")
def test_extract_analyse_generate_match_end_to_end(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))

    # 1. extract -> output enrichment present on the persisted document
    doc1 = _extract(client, _DOC1, "g1.md", "it_1805b")
    doc2 = _extract(client, _DOC2, "g2.md", "it_1805b")
    id1 = doc1["document"]["structure_document_id"]
    id2 = doc2["document"]["structure_document_id"]
    assert doc1["document"]["language_hints"] == ["en"]
    assert doc1["document"]["quality_score"] is not None
    assert doc1["document"]["metadata"]["quality"]["section_completeness"] == 1.0
    assert doc1["document"]["metadata"]["token_count"] > 0

    # 2. corpus analyse -> commonality / variation / distance matrix
    corp = client.post(
        api_tools_path("structure_corpus_create"),
        json={"corpus": {"name": "it 1805b", "profile_id": "default", "collection_id": "it_1805b", "document_ids": [id1, id2]}},
        headers=_ADMIN,
    )
    assert corp.status_code == 200, corp.text
    cid = corp.json()["corpus_id"]

    analysed = client.post(api_tools_path("structure_corpus_analyse"), json={"corpus_id": cid}, headers=_ADMIN)
    assert analysed.status_code == 200, analysed.text
    body = analysed.json()
    assert body["commonality_score"] == 1.0  # both docs share introduction->scope
    assert body["variation_score"] == 0.0
    assert len(body["distance_matrix"]) == 1
    assert body["distance_matrix"][0]["distance"] == 0.0
    assert body["mean_pairwise_distance"] == 0.0

    # 3. template generate
    tmpl = client.post(api_tools_path("structure_template_generate"), json={"corpus_id": cid, "name": "IT 1805B Template"}, headers=_ADMIN)
    assert tmpl.status_code == 200, tmpl.text
    tid = tmpl.json()["template_id"]

    # 4. template match (new tool) via MCP tools surface
    matched = client.post(
        api_tools_path("structure_template_match"),
        json={"template_id": tid, "structure_document_id": id1},
        headers=_ADMIN,
    )
    assert matched.status_code == 200, matched.text
    match_body = matched.json()
    assert match_body["match_score"] == 1.0
    assert [m["section_type"] for m in match_body["matched"]] == ["introduction", "scope"]
    assert match_body["missing"] == []
    assert match_body["extra"] == []

    # 4b. template match via REST surface
    rest = client.post(
        f"/api/v1/structure/templates/{tid}/match",
        json={"structure_document_id": id1},
        headers=_ADMIN,
    )
    assert rest.status_code == 200, rest.text
    assert rest.json()["match_score"] == 1.0

    # 5. RBAC: reader can read-match (collection.read); missing id -> 400
    reader_match = client.post(
        f"/api/v1/structure/templates/{tid}/match",
        json={"structure_document_id": id1},
        headers=_READER,
    )
    assert reader_match.status_code == 200, reader_match.text
    bad = client.post(f"/api/v1/structure/templates/{tid}/match", json={}, headers=_ADMIN)
    assert bad.status_code == 400

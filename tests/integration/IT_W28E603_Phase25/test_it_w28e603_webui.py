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

"""W28E-603 §25 #11 — server-rendered WebUI structure / corpus / template workflow page.

The page is rendered HTML served at /admin/ui/structure and wired to the /api/v1/structure/* endpoints
through the shared admin client script. This verifies the workflow surface + JS wiring exist; the
endpoints themselves are exercised end-to-end by IT_W28E603_Phase25 and the structure API tests.
"""


from __future__ import annotations
import pytest

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
@pytest.mark.IT
@pytest.mark.webui
@pytest.mark.req("FR-007")


def test_structure_webui_page_renders_workflow_controls(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    resp = client.get("/admin/ui/structure")
    assert resp.status_code == 200, resp.text
    html = resp.text
    # workflow controls present (inspection + corpus + templates)
    for testid in (
        "struct-extract-btn", "struct-docs-refresh", "struct-outline-btn",
        "corpus-create-btn", "corpus-list-btn", "corpus-analyse-btn", "corpus-patterns-btn",
        "template-generate-btn", "template-export-btn", "template-delete-btn",
    ):
        assert f'data-testid="{testid}"' in html, f"missing control {testid}"
    # the page is reachable from the admin navigation
    assert '/admin/ui/structure' in html
@pytest.mark.IT
@pytest.mark.webui
@pytest.mark.req("FR-007")


def test_structure_webui_script_wires_workflows(service: IndexService) -> None:
    client = TestClient(build_api_app(service=service))
    resp = client.get("/admin/ui/app.js")
    assert resp.status_code == 200
    js = resp.text
    for fn in ("structureExtract", "structureOutline", "corpusCreate", "corpusAnalyse", "corpusPatterns", "templateGenerate", "templateExport", "templateDelete", "bootstrapStructure"):
        assert fn in js, f"missing JS handler {fn}"
    # handlers target the structure API
    assert "/api/v1/structure/extract" in js
    assert "/api/v1/structure/corpora" in js
    assert "/api/v1/structure/templates" in js

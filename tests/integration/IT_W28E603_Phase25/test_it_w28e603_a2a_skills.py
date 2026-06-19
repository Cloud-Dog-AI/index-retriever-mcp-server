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

"""W28E-603 §25 #12 — A2A exposes selected structure skills (design brief §14)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from index_server.a2a_server import build_a2a_app
import pytest

_ADMIN = {"authorization": "Bearer valid-admin-token"}
_STRUCTURE_SKILLS = {
    "structure_extract",
    "structure_document_get",
    "structure_outline_get",
    "structure_corpus_create",
    "structure_corpus_analyse",
    "structure_corpus_patterns_get",
    "structure_template_generate",
    "structure_template_export",
    "structure_template_delete",
}
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_agent_card_advertises_structure_skills() -> None:
    client = TestClient(build_a2a_app())
    card = client.get("/.well-known/agent.json")
    assert card.status_code == 200
    skill_ids = {item["id"] for item in card.json()["skills"]}
    assert _STRUCTURE_SKILLS.issubset(skill_ids), f"missing A2A structure skills: {_STRUCTURE_SKILLS - skill_ids}"
@pytest.mark.IT
@pytest.mark.mcp
@pytest.mark.req("FR-007")


def test_a2a_structure_extract_skill_executes() -> None:
    client = TestClient(build_a2a_app())
    # missing auth is rejected
    denied = client.post("/a2a/tasks", json={"id": "x", "skill_id": "structure_extract", "input": {"text": "{}"}})
    assert denied.status_code == 401

    resp = client.post(
        "/a2a/tasks",
        headers=_ADMIN,
        json={
            "id": "a2a-struct-1",
            "skill_id": "structure_extract",
            "input": {"text": json.dumps({
                "text": "# Introduction\nIntro.\n\n# Scope\nScope.\n",
                "profile": "default",
                "collection": "a2a_struct",
                "source_filename": "a2a.md",
            })},
        },
    )
    assert resp.status_code == 200, resp.text
    out = resp.json()["output"]["json"]
    assert out["document"]["structure_document_id"]
    assert len(out["sections"]) == 2

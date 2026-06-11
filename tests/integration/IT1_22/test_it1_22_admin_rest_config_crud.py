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

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from index_tools.tools.service import IndexService
from tests.http_paths import api_tools_path


def test_admin_rest_profile_user_group_api_key_lifecycle(service: IndexService) -> None:
    # Covers: CFG-01, CFG-02, CFG-03, CFG-04, CFG-06, CFG-08, CFG-09, CFG-10, CFG-12, CFG-13
    client = TestClient(build_api_app(service=service))
    admin_headers = {"Authorization": "Bearer valid-admin-token"}
    backend = os.environ.get("CLOUD_DOG__INDEX__VDB__PROVIDER", "chroma").strip() or "chroma"

    create_profile = client.post(
        "/admin/profiles",
        json={"profile": "cfg_it", "config": {"backend": backend, "enabled": True, "roles": ["reader", "writer"]}},
        headers=admin_headers,
    )
    assert create_profile.status_code == 200, create_profile.text
    assert create_profile.json()["config"]["backend"] == backend

    list_profiles = client.get("/admin/profiles", headers=admin_headers)
    assert list_profiles.status_code == 200
    assert any(item["profile"] == "cfg_it" for item in list_profiles.json()["profiles"])

    update_profile = client.put(
        "/admin/profiles/cfg_it",
        json={"config": {"enabled": False, "default_collection": "cfg_docs"}},
        headers=admin_headers,
    )
    assert update_profile.status_code == 200
    assert update_profile.json()["config"]["enabled"] is False

    create_user = client.post(
        "/admin/users",
        json={"user_id": "cfg-user", "display_name": "Config User", "roles": ["reader"], "groups": ["ops"]},
        headers=admin_headers,
    )
    assert create_user.status_code == 200
    assert create_user.json()["user"]["user_id"] == "cfg-user"

    create_group = client.post(
        "/admin/groups",
        json={"group_id": "ops", "roles": ["reader", "writer"], "members": ["cfg-user"]},
        headers=admin_headers,
    )
    assert create_group.status_code == 200
    assert create_group.json()["group"]["group_id"] == "ops"

    create_key = client.post(
        "/admin/api-keys",
        json={
            "key_id": "cfg-it-key",
            "label": "Config IT Key",
            "roles": ["admin", "writer", "reader"],
            "capabilities": ["ingest", "query"],
            "user_id": "cfg-user",
        },
        headers=admin_headers,
    )
    assert create_key.status_code == 200, create_key.text
    token = create_key.json()["api_key"]["token"]
    key_headers = {"X-API-Key": token}

    create_collection = client.post(
        api_tools_path("admin_collection_create"),
        json={"profile": "cfg_it", "collection": "cfg_docs"},
        headers=key_headers,
    )
    assert create_collection.status_code == 200, create_collection.text

    ingest = client.post(
        api_tools_path("ingest_text"),
        json={
            "profile": "cfg_it",
            "collection": "cfg_docs",
            "text": "configuration crud integration payload",
            "source": "file://cfg-it/doc.txt",
        },
        headers=key_headers,
    )
    assert ingest.status_code == 200, ingest.text

    search = client.post(
        api_tools_path("search"),
        json={"profile": "cfg_it", "collection": "cfg_docs", "query": "integration payload"},
        headers=key_headers,
    )
    assert search.status_code == 200, search.text
    assert search.json()["results"]

    a2a_events = client.get("/a2a/events", headers=key_headers)
    assert a2a_events.status_code == 200, a2a_events.text
    event_types = {item["entity_type"] for item in a2a_events.json()["events"]}
    assert {"profile", "user", "group", "api_key"}.issubset(event_types)

    revoke = client.delete("/admin/api-keys/cfg-it-key", headers=admin_headers)
    assert revoke.status_code == 200
    assert revoke.json()["api_key"]["revoked"] is True

    delete_group = client.delete("/admin/groups/ops", headers=admin_headers)
    assert delete_group.status_code == 200
    delete_user = client.delete("/admin/users/cfg-user", headers=admin_headers)
    assert delete_user.status_code == 200
    delete_profile = client.delete("/admin/profiles/cfg_it", headers=admin_headers)
    assert delete_profile.status_code == 200


def test_admin_rest_rejects_non_admin_mutation(service: IndexService) -> None:
    # Covers: CFG-13
    client = TestClient(build_api_app(service=service))
    response = client.post(
        "/admin/profiles",
        json={"profile": "cfg_forbidden"},
        headers={"Authorization": "Bearer valid-writer-token"},
    )
    assert response.status_code == 403, response.text

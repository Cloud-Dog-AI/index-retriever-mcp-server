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

from tests.live_runtime import LiveIndexRuntime
import pytest
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.req("FR-004")


def test_multi_profile_cross_backend_metadata_parity(live_service: LiveIndexRuntime) -> None:
    providers = ["chroma", "qdrant"]
    if "infinity" in live_service._enabled_providers and live_service.backend_health_check(provider_id="infinity"):
        providers.append("infinity")

    invariants: list[tuple[str, str, str]] = []
    for provider_id in providers:
        profile = f"at_profile_{provider_id}"
        collection = f"at_parity_{provider_id}"
        source_uri = f"file://application/parity/{provider_id}/document.txt"
        live_service.admin_profile_create(profile, roles={"admin"})
        _ = live_service.ingest_text(
            profile=profile,
            collection=collection,
            text=f"{provider_id} parity payload token",
            source=source_uri,
            actor="application",
            provider_id=provider_id,
            metadata={"document_id": f"AT1-7-{provider_id.upper()}"},
        )
        rows = live_service.search(
            profile,
            collection,
            "parity payload",
            provider_id=provider_id,
            filters={"document_id": f"AT1-7-{provider_id.upper()}"},
            top_k=3,
        )
        assert rows
        metadata = rows[0]["metadata"]
        invariants.append(
            (
                str(metadata.get("source_uri", "")),
                str(metadata.get("filename", "")),
                str(metadata.get("mime_type", "")),
            )
        )

    assert invariants
    assert all(item[1] == "document.txt" for item in invariants)
    assert all(item[2] == "text/plain" for item in invariants)

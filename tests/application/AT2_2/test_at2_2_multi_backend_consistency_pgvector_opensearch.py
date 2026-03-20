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

import pytest

from tests.application.at2_helpers import build_live_runtime


@pytest.mark.timeout(300)
def test_at2_2_pgvector_opensearch_consistency() -> None:
    runtime = build_live_runtime()
    try:
        providers = ["pgvector", "opensearch"]
        missing = [provider_id for provider_id in providers if provider_id not in runtime._enabled_providers]
        if missing:
            pytest.fail("Providers not configured: " + ", ".join(missing), pytrace=False)
        unhealthy = [provider_id for provider_id in providers if not runtime.backend_health_check(provider_id=provider_id)]
        if unhealthy:
            pytest.fail("Providers not healthy: " + ", ".join(unhealthy), pytrace=False)

        snapshots: dict[str, dict[str, object]] = {}
        for provider_id in providers:
            collection = f"at2_2_{provider_id}"
            source_uri = f"file://at2/consistency/{provider_id}/doc.txt"
            rec = runtime.ingest_text(
                profile="default",
                collection=collection,
                text="W23A PGVector/OpenSearch parity payload.",
                source=source_uri,
                actor="application",
                provider_id=provider_id,
                metadata={"document_id": "AT2.2", "stage": "consistency"},
            )
            rows = runtime.search(
                "default",
                collection,
                "parity payload",
                provider_id=provider_id,
                top_k=3,
            )
            assert rows
            snapshots[provider_id] = {
                "record_id": rec.record_id,
                "content": str(rows[0]["content"]),
                "filename": str(rows[0]["metadata"].get("filename", "")),
                "mime_type": str(rows[0]["metadata"].get("mime_type", "")),
            }

        assert snapshots["pgvector"]["content"] == snapshots["opensearch"]["content"]
        assert snapshots["pgvector"]["filename"] == snapshots["opensearch"]["filename"] == "doc.txt"
        assert snapshots["pgvector"]["mime_type"] == snapshots["opensearch"]["mime_type"] == "text/plain"
    finally:
        runtime.cleanup()

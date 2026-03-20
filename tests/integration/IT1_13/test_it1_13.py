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


def test_source_metadata_round_trip(live_service: LiveIndexRuntime) -> None:
    source_uri = "file://integration/docs/metadata-check.pdf"
    _ = live_service.ingest_text(
        profile="default",
        collection="it_meta_roundtrip",
        text="metadata roundtrip token payload",
        source=source_uri,
        actor="integration",
        provider_id="chroma",
        metadata={"document_id": "IT1-13-DOC"},
    )
    rows = live_service.search(
        "default",
        "it_meta_roundtrip",
        "roundtrip",
        provider_id="chroma",
        filters={"document_id": "IT1-13-DOC"},
    )
    assert rows
    metadata = rows[0]["metadata"]
    assert metadata.get("source_uri") == source_uri
    assert metadata.get("filename") == "metadata-check.pdf"
    assert metadata.get("mime_type") == "application/pdf"

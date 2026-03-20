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


def test_full_workflow_upload_search_retrieve(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text(
        profile="default",
        collection="at_upload",
        text="application workflow payload",
        source="file://application/workflow.txt",
        actor="application",
        metadata={"document_id": "AT1-1-DOC", "source_hash": "sha256:workflow"},
    )
    rows = live_service.search("default", "at_upload", "workflow", filters={"document_id": "AT1-1-DOC"})
    assert rows
    record = live_service.retrieve("default", "at_upload", rec.record_id)
    assert record is not None
    assert "payload" in record.content
    assert record.metadata.get("document_id") == "AT1-1-DOC"
    assert record.metadata.get("source_uri") == "file://application/workflow.txt"
    assert record.metadata.get("lifecycle_state") == "active"
    assert record.metadata.get("indexing_signature")
    removed = live_service.delete_by_filter("default", "at_upload", {"document_id": "AT1-1-DOC"})
    assert removed >= 1

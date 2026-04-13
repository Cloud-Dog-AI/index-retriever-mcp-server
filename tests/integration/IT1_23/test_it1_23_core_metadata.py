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

from index_tools.tools.service import IndexService


def test_mt2_text_and_upload_ingest_store_canonical_metadata(service: IndexService) -> None:
    service.ingest_text(
        "default",
        "it_mt2_text",
        "canonical metadata text payload",
        "file://integration/it-mt2-text.txt",
        actor="integration",
    )
    service.ingest_upload(
        "default",
        "it_mt2_upload",
        "upload-metadata.txt",
        b"canonical metadata upload payload",
        actor="integration",
    )

    text_record = next(record for record in service.documents.values() if record.collection == "it_mt2_text")
    upload_record = next(record for record in service.documents.values() if record.collection == "it_mt2_upload")

    text_rows = service.search("default", "it_mt2_text", "canonical metadata text", top_k=5)
    upload_rows = service.search("default", "it_mt2_upload", "canonical metadata upload", top_k=5)

    assert text_rows[0]["doc_id"] == text_record.doc_id
    assert text_rows[0]["record_id"] == text_record.record_id
    assert text_rows[0]["source_uri"] == "file://integration/it-mt2-text.txt"
    assert text_rows[0]["content_hash"] == text_record.metadata["content_hash"]
    assert text_rows[0]["lifecycle_state"] == "active"

    upload_payload = service.retrieve(upload_record.record_id)
    assert upload_payload["source_uri"] == "upload://upload-metadata.txt"
    assert upload_payload["metadata"]["filename"] == "upload://upload-metadata.txt"
    assert upload_payload["metadata"]["mime_type"] == "text/plain"
    assert upload_payload["metadata"]["size_bytes"] == len(b"canonical metadata upload payload")
    assert upload_rows[0]["content_hash"] == upload_payload["content_hash"]


def test_mt2_preview_reports_parser_and_ocr_provenance(service: IndexService) -> None:
    preview = service.ingest_preview(
        text="column_a|column_b\n1|2",
        source_uri="file://integration/preview-metadata.txt",
        parser_chain=["internal"],
        ocr_mode="auto",
        table_policy="table_as_json",
    )

    assert preview["parser_provider"] == "internal"
    assert preview["ocr_mode"] == "auto"
    assert isinstance(preview["ocr_applied"], bool)
    assert any(step["stage"] == "parse" for step in preview["checkpoints"])


def test_mt3_mt4_round_trip_returns_latest_record_with_canonical_metadata(service: IndexService) -> None:
    service.ingest_text(
        "default",
        "it_mt34",
        "metadata version one",
        "file://integration/it-mt34.txt",
        actor="integration",
    )
    service.ingest_text(
        "default",
        "it_mt34",
        "metadata version two",
        "file://integration/it-mt34.txt",
        actor="integration",
    )

    latest_record = next(record for record in service.documents.values() if record.text == "metadata version two")
    old_record = next(record for record in service.documents.values() if record.text == "metadata version one")

    rows = service.search("default", "it_mt34", "metadata version", top_k=10)
    assert rows
    assert any(row["record_id"] == latest_record.record_id for row in rows)
    assert all(row["record_id"] != old_record.record_id for row in rows)
    assert all(row["lifecycle_state"] == "active" for row in rows)

    retrieved = service.retrieve(latest_record.record_id)
    assert retrieved["doc_id"] == latest_record.doc_id
    assert retrieved["record_id"] == latest_record.record_id
    assert retrieved["source_uri"] == "file://integration/it-mt34.txt"
    assert retrieved["content_hash"] == latest_record.metadata["content_hash"]
    assert retrieved["metadata"]["parser_provider"] == "internal"
    assert old_record.metadata["lifecycle_state"] == "superseded"
    assert old_record.metadata["is_latest"] is False

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

import json
from datetime import datetime, timedelta, timezone

from cloud_dog_vdb.lifecycle.manager import check_purge_safety, mark_deleted
from cloud_dog_vdb.lifecycle.retention import purge_candidates, ttl_expired
from cloud_dog_vdb.metadata.identity import compute_doc_id, compute_record_id, normalise_source_uri
from cloud_dog_vdb.metadata.schema import validate_metadata

from index_tools.pipeline.metadata import build_metadata
from index_tools.tools.service import IndexService
import pytest
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt1_build_metadata_emits_canonical_fields_and_passes_validation() -> None:
    payload = b"hello metadata"
    source = "file://docs/metadata-check.txt"

    metadata = build_metadata(source, payload, profile="default", collection="kb")

    assert metadata["source_uri"] == normalise_source_uri(source)
    assert metadata["content_hash"]
    assert metadata["doc_id"] == compute_doc_id(metadata["source_uri"], metadata["content_hash"])
    assert metadata["record_id"] == compute_record_id(metadata["doc_id"], 0)
    assert metadata["chunk_id"] == metadata["record_id"]
    assert metadata["lifecycle_state"] == "active"
    assert metadata["is_latest"] is True
    assert metadata["size_bytes"] == len(payload)
    assert metadata["created_at"].endswith("Z")
    assert metadata["ingested_at"].endswith("Z")
    assert len(json.dumps(metadata, sort_keys=True)) < 65536
    assert validate_metadata(metadata) == []
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt1_build_metadata_emits_metadata_pack_aliases() -> None:
    payload = b"hello metadata pack"
    source = "file://docs/metadata-pack.md"

    metadata = build_metadata(
        source,
        payload,
        profile="tenant-a",
        collection="collection-a",
        caller_metadata={
            "title": "Metadata Pack",
            "language": "en",
            "authoritative_source": True,
            "visibility": "restricted",
            "retention_class": "regulated",
        },
    )

    assert metadata["document_id"] == metadata["doc_id"]
    assert metadata["index_record_id"] == metadata["record_id"]
    assert metadata["dataset_id"] == "tenant-a"
    assert metadata["collection_id"] == "collection-a"
    assert metadata["title"] == "Metadata Pack"
    assert metadata["language"] == "en"
    assert metadata["status"] == "active"
    assert metadata["authoritative_source"] is True
    assert metadata["chunking_strategy"] == metadata["chunker"]
    assert metadata["pipeline_version"] == metadata["chunker_version"]
    assert metadata["normalisation_version"] == "v1"
    assert metadata["index_family"] == "index-retriever"
    assert metadata["visibility"] == "restricted"
    assert metadata["access_scope"] == "tenant-a"
    assert metadata["retention_class"] == "regulated"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt1_metadata_validation_rejects_invalid_enum_and_timestamp() -> None:
    metadata = build_metadata("file://docs/invalid-check.txt", b"hello", profile="default", collection="kb")

    broken_enum = dict(metadata)
    broken_enum["lifecycle_state"] = "broken"
    broken_time = dict(metadata)
    broken_time["created_at"] = "2026-04-12T12:00:00"

    assert any("lifecycle_state" in error for error in validate_metadata(broken_enum))
    assert any("created_at" in error for error in validate_metadata(broken_time))
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt1_build_metadata_is_deterministic_for_same_inputs() -> None:
    first = build_metadata("file://docs/deterministic.txt", b"repeatable", profile="default", collection="kb")
    second = build_metadata("file://docs/deterministic.txt", b"repeatable", profile="default", collection="kb")

    assert first["doc_id"] == second["doc_id"]
    assert first["record_id"] == second["record_id"]
    assert first["content_hash"] == second["content_hash"]
    assert first["source_hash"] == second["source_hash"]
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt4_same_content_reingest_reuses_canonical_identity(service: IndexService) -> None:
    service.ingest_text("default", "mt4_same", "same payload", "api://mt4/same", actor="writer")
    service.ingest_text("default", "mt4_same", "same payload", "api://mt4/same", actor="writer")

    records = [
        record
        for record in service.documents.values()
        if record.profile == "default" and record.collection == "mt4_same"
    ]

    assert len(records) == 1
    assert records[0].metadata["is_latest"] is True

    rows = service.search("default", "mt4_same", "same payload", top_k=10)
    assert len(rows) == 1
    assert rows[0]["doc_id"] == records[0].doc_id
    assert rows[0]["record_id"] == records[0].record_id
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt4_ingest_populates_embedding_dim_and_user_id(service: IndexService) -> None:
    service.ingest_text("default", "mt4_identity", "identity payload", "api://mt4/identity", actor="writer-user")

    record = next(record for record in service.documents.values() if record.collection == "mt4_identity")

    assert record.metadata["embedding_dim"] == service._embedding_dimension()
    assert record.metadata["user_id"] == "writer-user"
    assert record.metadata["embedding_dimensions"] == service._embedding_dimension()
    assert record.metadata["document_id"] == record.doc_id
    assert record.metadata["index_record_id"] == record.record_id
    assert record.metadata["collection_id"] == "mt4_identity"
    assert record.metadata["status"] == "active"
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt4_changed_content_marks_old_record_superseded_and_hides_it_from_default_search(
    service: IndexService,
) -> None:
    service.ingest_text("default", "mt4_version", "version one payload", "api://mt4/version", actor="writer")
    service.ingest_text("default", "mt4_version", "version two payload", "api://mt4/version", actor="writer")

    old_record = next(record for record in service.documents.values() if record.text == "version one payload")
    new_record = next(record for record in service.documents.values() if record.text == "version two payload")

    assert old_record.doc_id != new_record.doc_id
    assert old_record.record_id != new_record.record_id
    assert old_record.metadata["lifecycle_state"] == "superseded"
    assert old_record.metadata["status"] == "superseded"
    assert old_record.metadata["is_latest"] is False
    assert old_record.metadata["supersedes"] == new_record.record_id
    assert new_record.metadata["is_latest"] is True

    rows = service.search("default", "mt4_version", "version", top_k=10)
    assert rows
    assert any(row["record_id"] == new_record.record_id for row in rows)
    assert all(row["record_id"] != old_record.record_id for row in rows)
    assert all(row["is_latest"] is not False for row in rows)
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt4_search_filters_support_metadata_pack_fields_and_date_operators(service: IndexService) -> None:
    old_created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new_created = datetime(2026, 2, 1, tzinfo=timezone.utc)
    service.ingest_text(
        "default",
        "mt4_filter_pack",
        "older policy payload",
        "file://mt4/filter-old.md",
        actor="writer",
        metadata={"language": "en", "authoritative_source": True, "index_version": "v1"},
        created_at=old_created,
    )
    service.ingest_text(
        "default",
        "mt4_filter_pack",
        "newer policy payload",
        "file://mt4/filter-new.md",
        actor="writer",
        metadata={"language": "fr", "authoritative_source": False, "index_version": "v2"},
        created_at=new_created,
    )

    newer_rows = service.search(
        "default",
        "mt4_filter_pack",
        "policy payload",
        top_k=10,
        filters={"created_at": {"gte": "2026-01-15T00:00:00Z"}},
    )
    assert [row["source_uri"] for row in newer_rows] == ["file://mt4/filter-new.md"]

    exact_rows = service.search(
        "default",
        "mt4_filter_pack",
        "policy payload",
        top_k=10,
        filters={
            "dataset_id": "default",
            "collection_id": "mt4_filter_pack",
            "language": "en",
            "authoritative_source": True,
            "index_version": "v1",
        },
    )
    assert [row["source_uri"] for row in exact_rows] == ["file://mt4/filter-old.md"]
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt5_deleted_record_is_hidden_from_search_results(service: IndexService) -> None:
    service.ingest_text("default", "mt5_delete", "delete me payload", "api://mt5/delete", actor="writer")

    record = next(record for record in service.documents.values() if record.collection == "mt5_delete")
    assert service.delete_by_id("default", "mt5_delete", str(record.record_id or record.doc_id)) is True
    assert record.metadata["status"] == "deleted"

    rows = service.search("default", "mt5_delete", "delete me payload", top_k=10)
    assert rows == []
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt5_delete_by_id_marks_local_record_deleted_when_backend_delete_returns_false(
    service: IndexService,
    monkeypatch,
) -> None:
    service.ingest_text("default", "mt5_delete_fallback", "delete fallback payload", "api://mt5/delete-fallback", actor="writer")
    record = next(record for record in service.documents.values() if record.collection == "mt5_delete_fallback")

    async def _delete_record(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(service.vdb, "delete_record", _delete_record)

    assert service.delete_by_id("default", "mt5_delete_fallback", str(record.record_id or record.doc_id)) is True
    assert record.metadata["lifecycle_state"] == "deleted"
    assert service.search("default", "mt5_delete_fallback", "delete fallback payload", top_k=10) == []
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt5_delete_by_filter_marks_local_records_deleted_when_backend_returns_zero(
    service: IndexService,
    monkeypatch,
) -> None:
    service.ingest_text("default", "mt5_delete_filter", "filter fallback payload", "api://mt5/filter-fallback", actor="writer")
    record = next(record for record in service.documents.values() if record.collection == "mt5_delete_filter")

    async def _delete_by_filter(*_args, **_kwargs) -> int:
        return 0

    monkeypatch.setattr(service.vdb, "delete_by_filter", _delete_by_filter)

    deleted = service.delete_by_filter(
        "default",
        "mt5_delete_filter",
        {"source_uri": "api://mt5/filter-fallback"},
    )
    assert deleted == 1
    assert record.metadata["lifecycle_state"] == "deleted"
    assert service.search("default", "mt5_delete_filter", "filter fallback payload", top_k=10) == []
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")


def test_mt5_retention_skips_archived_records_and_ttl_expiry_identifies_candidates(service: IndexService) -> None:
    created_at = datetime.now(timezone.utc) - timedelta(days=200)  # noqa: UP017

    service.ingest_text(
        "default",
        "mt5_retention",
        "archived payload",
        "api://mt5/archived",
        actor="writer",
        created_at=created_at,
    )
    archived_record = next(record for record in service.documents.values() if record.text == "archived payload")
    archived_record.metadata["lifecycle_state"] = "archived"

    assert service.retention_run("default", "mt5_retention", older_than_days=90) == 0
    assert archived_record.metadata["lifecycle_state"] == "archived"

    candidate = {
        "record_id": archived_record.record_id,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "ttl_days": 30,
        "lifecycle_state": "deleted",
        "is_latest": False,
    }

    deleted_candidate = mark_deleted(candidate)
    assert check_purge_safety(deleted_candidate) is True
    assert ttl_expired(deleted_candidate, now=datetime.now(timezone.utc)) is True  # noqa: UP017
    assert purge_candidates([deleted_candidate], now=datetime.now(timezone.utc)) == [deleted_candidate]  # noqa: UP017

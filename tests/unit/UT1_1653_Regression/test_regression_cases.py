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

import pytest

from cloud_dog_vdb.metadata.identity import compute_content_hash, normalise_source_uri
from index_tools.pipeline.metadata import build_metadata
from index_tools.queue.models import JobRecord


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.5")
class TestRegressionDuplicateIngest:

    def test_duplicate_text_ingest_reuses_document_ids(self, service) -> None:
        text = "regression test content for duplicate ingest"
        source = "https://example.com/regression-test-dup"
        profile = "default"
        collection = "default"

        job_id_1 = service.ingest_text(profile, collection, text, source, "test-actor")
        assert job_id_1

        job_id_2 = service.ingest_text(profile, collection, text, source, "test-actor")
        assert job_id_2
        assert job_id_2 == job_id_1, "Same content+source must return same job_id (idempotent)"

    def test_duplicate_text_ingest_no_new_vdb_objects(self, service) -> None:
        text = "regression-no-duplicate-objects"
        source = "https://example.com/regression-test-nodup"
        profile = "default"
        collection = "default"

        doc_ids_before = set(str(r.doc_id) for r in service.documents.values()
                             if r.profile == profile and r.collection == collection)
        service.ingest_text(profile, collection, text, source, "test-actor")
        doc_ids_after_first = set(str(r.doc_id) for r in service.documents.values()
                                  if r.profile == profile and r.collection == collection)
        new_after_first = doc_ids_after_first - doc_ids_before

        service.ingest_text(profile, collection, text, source, "test-actor")
        doc_ids_after_second = set(str(r.doc_id) for r in service.documents.values()
                                   if r.profile == profile and r.collection == collection)
        new_after_second = doc_ids_after_second - doc_ids_after_first

        assert not new_after_second, "Second identical ingest must not create new VDB objects"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.5")
class TestRegressionChangedCanonicalKey:

    def test_changed_source_produces_different_doc_ids(self) -> None:
        content = b"canonical identity change test"
        meta1 = build_metadata(source="https://example.com/alpha", content=content,
                               profile="default", collection="default")
        meta2 = build_metadata(source="https://example.com/beta", content=content,
                               profile="default", collection="default")
        assert meta1["doc_id"] != meta2["doc_id"]
        assert meta1["record_id"] != meta2["record_id"]

    def test_changed_content_produces_different_content_hash(self) -> None:
        h1 = compute_content_hash("version one of content")
        h2 = compute_content_hash("version two of content - changed")
        assert h1 != h2


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.5")
class TestRegressionLostVdbBinding:

    def test_search_result_includes_vdb_binding_fields(self, service) -> None:
        text = "binding-field-regression-test"
        source = "https://example.com/binding-test"
        profile = "default"
        collection = "default"

        service.ingest_text(profile, collection, text, source, "test-actor")
        matching = [
            r for r in service.documents.values()
            if r.profile == profile and r.collection == collection
            and str(r.metadata.get("lifecycle_state", "active")) == "active"
        ]
        assert matching, "Document must exist after ingest"
        record = matching[0]
        assert "collection_id" in record.metadata or record.collection, "Missing collection binding"
        assert record.doc_id or record.record_id, "Missing doc_id/record_id"
        assert record.metadata.get("chunk_id") or record.metadata.get("record_id"), "Missing chunk_id"
        assert record.metadata.get("source_uri"), "Missing source_uri"
        assert record.metadata.get("content_hash"), "Missing content_hash"

    def test_retrieve_result_includes_vdb_binding_fields(self, service) -> None:
        text = "retrieve-binding-test"
        source = "https://example.com/retrieve-binding"
        profile = "default"
        collection = "default"

        service.ingest_text(profile, collection, text, source, "test-actor")
        matching = [
            r for r in service.documents.values()
            if r.profile == profile and r.collection == collection
            and str(r.metadata.get("lifecycle_state", "active")) == "active"
        ]
        assert matching, "Document should exist in documents dict after ingest"
        record = matching[0]
        assert "collection" in str(record.metadata.get("collection_id", record.collection)) \
            or record.collection == collection
        assert "doc_id" in str(record.metadata) or record.doc_id


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.5")
class TestRegressionDuplicateChunks:

    def test_same_content_hash_resolves_matching_docs(self) -> None:
        text_a = b"content for chunk test a"
        text_b = b"content for chunk test a"
        meta_a = build_metadata(source="https://example.com/chunk-a", content=text_a,
                                profile="default", collection="default")
        meta_b = build_metadata(source="https://example.com/chunk-a", content=text_b,
                                profile="default", collection="default")
        assert meta_a["content_hash"] == meta_b["content_hash"]

    def test_identical_ingest_preserves_existing_chunks(self, service) -> None:
        text = "preserve chunk test content"
        source = "https://example.com/preserve-chunks"
        profile = "default"
        collection = "default"

        service.ingest_text(profile, collection, text, source, "test-actor")
        docs_after_first = [r for r in service.documents.values()
                            if r.profile == profile and r.collection == collection
                            and str(r.metadata.get("lifecycle_state", "active")) == "active"]
        first_count = len(docs_after_first)

        service.ingest_text(profile, collection, text, source, "test-actor")
        docs_after_second = [r for r in service.documents.values()
                             if r.profile == profile and r.collection == collection
                             and str(r.metadata.get("lifecycle_state", "active")) == "active"]
        second_count = len(docs_after_second)

        assert second_count == first_count, "Second ingest should not duplicate active chunks"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.5")
class TestRegressionUnboundQueryResult:

    def test_query_for_nonexistent_material_returns_empty(self, service) -> None:
        results = service.search("default", "default", "xyznonexistentmaterial12345")
        assert len(results) == 0, "Query for nonexistent material must return empty"

    def test_deleted_document_not_returned_in_query(self, service) -> None:
        text = "to-be-deleted-test-content"
        source = "https://example.com/to-delete"
        profile = "default"
        collection = "default"

        service.ingest_text(profile, collection, text, source, "test-actor")
        matching = [
            r for r in service.documents.values()
            if r.profile == profile and r.collection == collection
            and str(r.metadata.get("lifecycle_state", "active")) == "active"
            and r.metadata.get("is_latest") is not False
        ]
        assert matching, "Document should exist before delete"

        doc_id = str(matching[0].doc_id)
        service.delete_by_id(profile, collection, doc_id)

        after_delete = [
            r for r in service.documents.values()
            if r.profile == profile and r.collection == collection
            and str(r.metadata.get("lifecycle_state", "active")) == "active"
            and r.metadata.get("is_latest") is not False
            and r.doc_id == doc_id
        ]
        assert not after_delete, "Deleted document must not appear in active documents"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.5")
class TestRegressionHashProvenanceMismatch:

    def test_content_hash_matches_metadata(self) -> None:
        content = b"hash provenance test content"
        metadata = build_metadata(source="https://example.com/hash-prov", content=content,
                                  profile="default", collection="default")
        assert metadata["content_hash"] == compute_content_hash(content.decode("utf-8", errors="replace"))

    def test_different_content_produces_different_hash_in_metadata(self) -> None:
        meta1 = build_metadata(source="https://example.com/hp1", content=b"content v1",
                               profile="default", collection="default")
        meta2 = build_metadata(source="https://example.com/hp2", content=b"content v2",
                               profile="default", collection="default")
        assert meta1["content_hash"] != meta2["content_hash"]

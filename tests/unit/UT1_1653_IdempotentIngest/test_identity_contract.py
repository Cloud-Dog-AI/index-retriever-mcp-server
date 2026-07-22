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

from hashlib import sha256

import pytest

from cloud_dog_vdb.metadata.identity import compute_content_hash, normalise_source_uri
from index_tools.pipeline.metadata import build_metadata


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.1")
class TestIngestIdentityContract:

    def test_content_hash_is_stable(self) -> None:
        text = "idempotent ingest test content"
        h1 = compute_content_hash(text)
        h2 = compute_content_hash(text)
        assert h1 == h2
        assert len(h1) == 64

    def test_different_content_produces_different_hash(self) -> None:
        h1 = compute_content_hash("content alpha")
        h2 = compute_content_hash("content beta")
        assert h1 != h2

    def test_source_uri_normalised(self) -> None:
        uri = "https://example.com/data?v=1#section"
        norm = normalise_source_uri(uri)
        assert "example.com/data" in norm

    def test_build_metadata_produces_canonical_ids(self) -> None:
        source = "https://en.wikipedia.org/wiki/Test"
        content = b"canonical test content for identity"
        metadata = build_metadata(
            source=source,
            content=content,
            profile="default",
            collection="test-collection",
        )
        assert "doc_id" in metadata
        assert "record_id" in metadata
        assert "content_hash" in metadata
        assert "source_uri" in metadata
        assert metadata["source_uri"] == normalise_source_uri(source)
        assert metadata["collection_id"] == "test-collection"
        assert metadata["chunk_id"] == metadata["record_id"]
        assert len(metadata["doc_id"]) > 0
        assert len(metadata["record_id"]) > 0

    def test_metadata_includes_collection_binding(self) -> None:
        metadata = build_metadata(
            source="https://example.com/doc.txt",
            content=b"collection binding test",
            profile="default",
            collection="my-collection",
        )
        assert metadata["collection_id"] == "my-collection"
        assert metadata["profile"] == "default"
        assert metadata["namespace"] == "default:my-collection"

    def test_same_input_produces_same_canonical_ids(self) -> None:
        meta1 = build_metadata(
            source="https://example.com/same",
            content=b"same content",
            profile="default",
            collection="default",
        )
        meta2 = build_metadata(
            source="https://example.com/same",
            content=b"same content",
            profile="default",
            collection="default",
        )
        assert meta1["doc_id"] == meta2["doc_id"]
        assert meta1["record_id"] == meta2["record_id"]
        assert meta1["content_hash"] == meta2["content_hash"]

    def test_different_source_produces_different_canonical_ids(self) -> None:
        meta1 = build_metadata(
            source="https://example.com/alpha",
            content=b"same content",
            profile="default",
            collection="default",
        )
        meta2 = build_metadata(
            source="https://example.com/beta",
            content=b"same content",
            profile="default",
            collection="default",
        )
        assert meta1["doc_id"] != meta2["doc_id"]

    def test_query_linkage_fields_present(self) -> None:
        metadata = build_metadata(
            source="https://example.com/query-link",
            content=b"query linkage test content",
            profile="default",
            collection="default",
        )
        linkage_fields = ["doc_id", "record_id", "chunk_id", "content_hash", "source_uri", "collection_id"]
        for field in linkage_fields:
            assert field in metadata, f"Missing linkage field: {field}"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("W28M-1653.1")
class TestIdempotencyKeyGeneration:

    def test_idempotency_key_is_sha256(self, service) -> None:
        key = service.queue.generate_idempotency_key("default", "col", "https://example.com:abc123")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_same_input_produces_same_key(self, service) -> None:
        k1 = service.queue.generate_idempotency_key("default", "col", "source")
        k2 = service.queue.generate_idempotency_key("default", "col", "source")
        assert k1 == k2

    def test_different_profile_produces_different_key(self, service) -> None:
        k1 = service.queue.generate_idempotency_key("p1", "col", "source")
        k2 = service.queue.generate_idempotency_key("p2", "col", "source")
        assert k1 != k2

    def test_different_collection_produces_different_key(self, service) -> None:
        k1 = service.queue.generate_idempotency_key("default", "c1", "source")
        k2 = service.queue.generate_idempotency_key("default", "c2", "source")
        assert k1 != k2

    def test_different_source_produces_different_key(self, service) -> None:
        k1 = service.queue.generate_idempotency_key("default", "col", "source-a")
        k2 = service.queue.generate_idempotency_key("default", "col", "source-b")
        assert k1 != k2

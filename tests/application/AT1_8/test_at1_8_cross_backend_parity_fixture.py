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

import asyncio
import importlib.util
from pathlib import Path
from typing import Any

import pytest

from cloud_dog_vdb import CollectionSpec, Record, SearchRequest, get_vdb_client

from index_tools.pipeline.metadata import build_metadata
from tests.w23a_helpers import backend_available, runtime_backend_store


def _load_metadata_parity_helper():
    helper_path = (
        Path(__file__).resolve().parents[4]
        / "cloud-dog-ai-platform-standards"
        / "packages"
        / "backend"
        / "platform-vdb"
        / "tests"
        / "integration"
        / "_metadata_parity.py"
    )
    spec = importlib.util.spec_from_file_location("platform_vdb_metadata_parity", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load metadata parity helper from {helper_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.assert_metadata_field_parity


async def _run_parity_validation() -> dict[str, dict[str, Any]]:
    candidate_provider_ids = [
        provider_id
        for provider_id in ("chroma", "qdrant", "opensearch", "pgvector", "weaviate")
        if backend_available(provider_id)
    ]
    if len(candidate_provider_ids) < 2:
        pytest.fail("Fewer than two VDB backends are available for parity validation")

    runtime_config = {
        "vector_stores": {
            "default_backend": candidate_provider_ids[0],
            **{provider_id: runtime_backend_store(provider_id) for provider_id in candidate_provider_ids},
        }
    }
    client = get_vdb_client(runtime_config)
    provider_ids: list[str] = []
    blocked: dict[str, str] = {}
    for provider_id in candidate_provider_ids:
        probe_collection = f"cloud_dog_ai_meta_parity_{provider_id}_probe"
        try:
            await client.create_collection(
                CollectionSpec(name=probe_collection, namespace="parity", embedding_dim=4),
                provider_id=provider_id,
            )
            provider_ids.append(provider_id)
        except Exception as exc:
            blocked[provider_id] = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                await client.delete_collection(probe_collection, provider_id=provider_id)
            except Exception:
                pass
    if len(provider_ids) < 2:
        pytest.fail(f"Fewer than two parity-capable backends are available: blocked={blocked}")

    metadata = build_metadata(
        source="file://parity/document.txt",
        content=b"cross backend parity payload",
        profile="default",
        collection="parity_contract",
    )
    metadata = {
        key: metadata.get(key)
        for key in (
            "doc_id",
            "record_id",
            "source_uri",
            "source_type",
            "filename",
            "mime_type",
            "content_hash",
            "source_hash",
            "created_at",
            "ingested_at",
            "modified_at",
            "lifecycle_state",
            "tenant_id",
            "namespace",
            "profile",
            "collection",
            "parser_provider",
            "parser_version",
            "ocr_engine",
            "ocr_confidence",
            "ocr_applied",
            "page",
            "page_number",
            "table_id",
            "chunk_kind",
        )
    }

    assert_metadata_field_parity = _load_metadata_parity_helper()
    fields = await assert_metadata_field_parity(
        client,
        provider_ids=provider_ids,
        metadata=metadata,
        filters={"tenant_id": "default", "namespace": "default:parity_contract"},
    )
    expected_fields = {
        "doc_id",
        "record_id",
        "source_uri",
        "content_hash",
        "lifecycle_state",
        "tenant_id",
        "namespace",
    }
    assert expected_fields <= fields

    observed: dict[str, dict[str, Any]] = {}
    for provider_id in provider_ids:
        collection = f"at1_8_parity_{provider_id}"
        try:
            await client.delete_collection(collection, provider_id=provider_id)
        except Exception:
            pass

        await client.create_collection(
            CollectionSpec(name=collection, namespace="parity", embedding_dim=8),
            provider_id=provider_id,
        )
        try:
            await client.upsert_records(
                collection,
                [Record(record_id=f"at1-8-{provider_id}", content="cross backend parity payload", metadata=dict(metadata))],
                provider_id=provider_id,
            )
            rows = await client.search(
                collection,
                SearchRequest(
                    query_text="parity payload",
                    top_k=5,
                    filters={"tenant_id": "default", "namespace": "default:parity_contract"},
                ),
                provider_id=provider_id,
            )
            assert rows.results, f"no search rows returned for provider {provider_id}"
            row_payload = dict(rows.results[0].payload)
            row_metadata = dict(row_payload.get("metadata", {}))
            observed[provider_id] = {
                "doc_id": str(row_metadata.get("doc_id", "")),
                "content_hash": str(row_metadata.get("content_hash", "")),
                "fields": set(row_metadata.keys()),
            }
            deleted = await client.delete_by_filter(
                collection,
                {"doc_id": str(row_metadata.get("doc_id", ""))},
                provider_id=provider_id,
            )
            assert int(deleted) >= 1
            remaining = await client.list_records(
                collection,
                filters={"doc_id": str(row_metadata.get("doc_id", ""))},
                paging={"offset": 0, "limit": 10},
                provider_id=provider_id,
            )
            assert remaining
            assert all(str(item.metadata.get("lifecycle_state", "")) == "deleted" for item in remaining)
        finally:
            await client.delete_collection(collection, provider_id=provider_id)

    return observed
@pytest.mark.AT
@pytest.mark.mcp
@pytest.mark.req("FR-004")


def test_cross_backend_parity_fixture_and_contract() -> None:
    observed = asyncio.run(_run_parity_validation())
    assert observed
    baseline_provider = next(iter(observed))
    baseline = observed[baseline_provider]
    for provider_id, payload in observed.items():
        assert payload["doc_id"] == baseline["doc_id"], provider_id
        assert payload["content_hash"] == baseline["content_hash"], provider_id
        assert payload["fields"] == baseline["fields"], provider_id

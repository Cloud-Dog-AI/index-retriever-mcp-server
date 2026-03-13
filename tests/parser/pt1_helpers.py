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

# index-retriever-mcp-server — PT1 Helpers
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared performance baseline helpers for W23A PT1 suites.

from __future__ import annotations

import asyncio
import time
from statistics import mean
from typing import Any

from cloud_dog_vdb import CollectionSpec, Record, SearchRequest

from tests.integration.it2_matrix_helpers import parse_pdf_with_provider
from tests.w23a_helpers import (
    VDB_PROVIDER_IDS,
    backend_available,
    build_vdb_client,
    corpus_file,
    parser_available,
    write_artifact_json,
)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = max(0.0, min(1.0, p)) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return float(ordered[low] * (1.0 - frac) + ordered[high] * frac)


async def ingest_baseline_for_provider(provider_id: str, *, documents: int = 10) -> dict[str, Any]:
    client = build_vdb_client(provider_id, timeout_seconds=180)
    collection = f"w23a_pt1_ingest_{provider_id}"
    try:
        await client.delete_collection(collection, provider_id=provider_id)
    except Exception:
        pass

    start = time.perf_counter()
    created = False
    try:
        await client.create_collection(CollectionSpec(name=collection, embedding_dim=8), provider_id=provider_id)
        created = True
        durations_ms: list[float] = []
        for index in range(documents):
            step_start = time.perf_counter()
            await client.upsert_records(
                collection,
                [
                    Record(
                        record_id=f"pt1-{provider_id}-{index}",
                        content=f"PT1 ingest payload {provider_id} #{index}",
                        metadata={
                            "tenant_id": "pt1",
                            "index": index,
                            "source_uri": f"api://w23a/pt1/ingest/{provider_id}/{index}",
                            "source_type": "api",
                        },
                    )
                ],
                provider_id=provider_id,
            )
            durations_ms.append((time.perf_counter() - step_start) * 1000.0)
        total_ms = (time.perf_counter() - start) * 1000.0
        count = await client.count_documents(collection, provider_id=provider_id)
        return {
            "provider_id": provider_id,
            "documents": documents,
            "count": int(count),
            "total_ms": total_ms,
            "avg_ms_per_doc": mean(durations_ms) if durations_ms else 0.0,
            "p50_ms": percentile(durations_ms, 0.50),
            "p95_ms": percentile(durations_ms, 0.95),
            "p99_ms": percentile(durations_ms, 0.99),
        }
    finally:
        if created:
            try:
                await client.delete_collection(collection, provider_id=provider_id)
            except Exception:
                pass


async def search_latency_for_provider(provider_id: str, *, queries: int = 30) -> dict[str, Any]:
    client = build_vdb_client(provider_id, timeout_seconds=180)
    collection = f"w23a_pt1_search_{provider_id}"
    try:
        await client.delete_collection(collection, provider_id=provider_id)
    except Exception:
        pass

    created = False
    try:
        await client.create_collection(CollectionSpec(name=collection, embedding_dim=8), provider_id=provider_id)
        created = True
        records = [
            Record(
                record_id=f"search-{provider_id}-{index}",
                content=f"PT1 search payload {provider_id} #{index}",
                metadata={
                    "tenant_id": "pt1",
                    "bucket": index % 3,
                    "source_uri": f"api://w23a/pt1/search/{provider_id}/{index}",
                    "source_type": "api",
                },
            )
            for index in range(20)
        ]
        await client.upsert_records(collection, records, provider_id=provider_id)

        latencies_ms: list[float] = []
        for index in range(queries):
            start = time.perf_counter()
            response = await client.search(
                collection,
                SearchRequest(query_text="payload", top_k=5, filters={"tenant_id": "pt1"}),
                provider_id=provider_id,
            )
            _ = response
            latencies_ms.append((time.perf_counter() - start) * 1000.0)

        return {
            "provider_id": provider_id,
            "queries": queries,
            "p50_ms": percentile(latencies_ms, 0.50),
            "p95_ms": percentile(latencies_ms, 0.95),
            "p99_ms": percentile(latencies_ms, 0.99),
            "avg_ms": mean(latencies_ms) if latencies_ms else 0.0,
        }
    finally:
        if created:
            try:
                await client.delete_collection(collection, provider_id=provider_id)
            except Exception:
                pass


def available_backends() -> list[str]:
    return [provider_id for provider_id in VDB_PROVIDER_IDS if backend_available(provider_id)]


def available_parsers() -> list[str]:
    return [provider_id for provider_id in ("deepdoc", "docling", "mineru", "marker_mcp", "transformers", "internal") if parser_available(provider_id)]


def parser_throughput_case(provider_id: str) -> dict[str, Any]:
    source = corpus_file("Examples.pdf", "Z83-example.pdf")
    start = time.perf_counter()
    out = asyncio.run(parse_pdf_with_provider(provider_id, source_path=source))
    elapsed = max(time.perf_counter() - start, 1e-6)
    text_chars = int(out["text_chars"])
    return {
        "provider_id": provider_id,
        "file": source.name,
        "elapsed_seconds": elapsed,
        "text_chars": text_chars,
        "chars_per_second": text_chars / elapsed,
        "table_blocks": int(out["table_blocks"]),
    }


def write_pt_artifact(name: str, payload: dict[str, Any]) -> None:
    _ = write_artifact_json(name, payload)

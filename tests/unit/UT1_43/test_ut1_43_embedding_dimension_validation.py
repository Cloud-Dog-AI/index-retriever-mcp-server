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

from pathlib import Path

import pytest

from index_tools.tools.service import IndexService


def test_embedding_dimensions_match_and_mismatch_rejected(tmp_path: Path) -> None:
    service = IndexService(
        audit_path=str(tmp_path / "audit.jsonl"),
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        default_backend="chroma",
    )

    _ = service.ingest_text(
        profile="default",
        collection="ut1_43_embed",
        text="embedding dimension baseline payload",
        source="file://ut1_43/baseline.txt",
        actor="unit-test",
    )

    collection_key = "default:ut1_43_embed"
    stored = service.vdb.collections[collection_key]
    assert stored
    baseline_dims = {len(vector) for doc in stored.values() for vector in doc.vectors}
    assert baseline_dims == {8}

    original_embed = service.embedding_adapter.embed

    def _mismatched_embed(texts: list[str], dimensions: int = 8) -> list[list[float]]:
        _ = dimensions
        return [[1.0] * 6 for _ in texts]

    service.embedding_adapter.embed = _mismatched_embed
    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        _ = service.ingest_text(
            profile="default",
            collection="ut1_43_embed",
            text="embedding dimension mismatch payload",
            source="file://ut1_43/mismatch.txt",
            actor="unit-test",
        )
    service.embedding_adapter.embed = original_embed

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

from index_tools.tools.service import IndexService


def test_embedding_dimensions_match_and_mismatch_rejected(tmp_path: Path) -> None:
    service = IndexService(
        audit_path=str(tmp_path / "audit.jsonl"),
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        default_backend="chroma",
    )

    provider_id = service._profile_provider("default")
    backend_collection = service._ensure_backend_collection("default", "ut1_43_embed")
    created = service._run_async(service.vdb.get_collection(backend_collection, provider_id=provider_id))

    assert created is not None
    baseline_dim = int(created["embedding_dim"])
    assert baseline_dim > 0

    repeated_backend_collection = service._ensure_backend_collection("default", "ut1_43_embed")
    repeated = service._run_async(service.vdb.get_collection(repeated_backend_collection, provider_id=provider_id))

    assert repeated_backend_collection == backend_collection
    assert repeated is not None
    assert int(repeated["embedding_dim"]) == baseline_dim

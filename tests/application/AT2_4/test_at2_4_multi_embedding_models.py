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

import pytest

from tests.application.at2_helpers import build_live_runtime, temporary_env
from tests.w23a_helpers import embedding_matrix, write_artifact_json


@pytest.mark.timeout(600)
def test_at2_4_embedding_model_matrix() -> None:
    matrix = embedding_matrix()
    if not matrix:
        pytest.fail("No embedding model endpoints configured via env/Vault", pytrace=False)

    results: list[dict[str, object]] = []
    for config in matrix:
        model = str(config.get("model", "")).strip()
        base_url = str(config.get("base_url", "")).strip()
        if not model or not base_url:
            continue

        env_overrides = {
            "CLOUD_DOG__INDEX__EMBEDDING__MODEL": model,
            "CLOUD_DOG__INDEX__EMBEDDING__BASE_URL": base_url,
            "EMBED_BASE_URL": base_url,
        }
        api_key = str(config.get("api_key", "")).strip()
        if api_key:
            env_overrides["CLOUD_DOG__INDEX__EMBEDDING__API_KEY"] = api_key
            env_overrides["EMBED_API_KEY"] = api_key

        with temporary_env(env_overrides):
            runtime = build_live_runtime()
            try:
                if "chroma" not in runtime._enabled_providers:
                    pytest.fail("chroma backend required for AT2.4 model matrix", pytrace=False)
                if not runtime.backend_health_check(provider_id="chroma"):
                    pytest.fail("chroma backend unhealthy for AT2.4 model matrix", pytrace=False)

                embedding_dim = runtime._embedding_dimension()
                rec = runtime.ingest_text(
                    profile="default",
                    collection="at2_4_embedding",
                    text=f"W23A embedding model payload for {model}",
                    source=f"file://at2/embedding/{model}.txt",
                    actor="application",
                    provider_id="chroma",
                    metadata={"embedding_model": model, "stage": "AT2.4"},
                    indexing_signature=model,
                )
                rows = runtime.search(
                    "default",
                    "at2_4_embedding",
                    f"payload {model}",
                    provider_id="chroma",
                    filters={"embedding_model": model},
                    top_k=5,
                )
                assert rows
                results.append(
                    {
                        "model": model,
                        "embedding_dim": int(embedding_dim),
                        "top_score": float(rows[0]["score"]),
                        "record_id": rec.record_id,
                    }
                )
            finally:
                runtime.cleanup()

    assert results
    _ = write_artifact_json("W23A-AT2.4-embedding-model-matrix.json", {"results": results})

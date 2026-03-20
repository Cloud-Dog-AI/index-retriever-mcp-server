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

from hashlib import sha256
from typing import Any, cast

try:
    import cloud_dog_llm  # type: ignore
except ImportError:  # pragma: no cover
    cloud_dog_llm = None


class EmbeddingAdapter:
    """Adapter wrapper for cloud_dog_llm embedding clients."""

    def __init__(self, provider: str, model: str) -> None:
        """Initialise the instance state."""
        self.provider = provider
        self.model = model

    def embed(self, texts: list[str], dimensions: int = 8) -> list[list[float]]:
        """Execute embed."""
        # Covers: FR-12
        if cloud_dog_llm is not None and hasattr(cloud_dog_llm, "embed"):
            response: Any = cloud_dog_llm.embed(provider=self.provider, model=self.model, inputs=texts)
            return cast(list[list[float]], response)

        vectors: list[list[float]] = []
        for text in texts:
            digest = sha256(text.encode("utf-8")).digest()
            values = [round(byte / 255.0, 6) for byte in digest[:dimensions]]
            vectors.append(values)
        return vectors

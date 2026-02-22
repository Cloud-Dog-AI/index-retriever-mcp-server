# index-retriever-mcp-server — Embedding Adapter
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Embedding adapter delegating to cloud_dog_llm.

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
        self.provider = provider
        self.model = model

    def embed(self, texts: list[str], dimensions: int = 8) -> list[list[float]]:
        if cloud_dog_llm is not None and hasattr(cloud_dog_llm, "embed"):
            response: Any = cloud_dog_llm.embed(provider=self.provider, model=self.model, inputs=texts)
            return cast(list[list[float]], response)

        vectors: list[list[float]] = []
        for text in texts:
            digest = sha256(text.encode("utf-8")).digest()
            values = [round(byte / 255.0, 6) for byte in digest[:dimensions]]
            vectors.append(values)
        return vectors

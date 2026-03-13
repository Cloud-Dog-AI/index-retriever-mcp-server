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

# index-retriever-mcp-server — Embedding Registry
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Registry for cloud_dog_llm embedding adapters.

from __future__ import annotations

from collections.abc import Callable

EmbeddingFn = Callable[[list[str]], list[list[float]]]


class EmbeddingRegistry:
    """Registry of embedding provider adapters by profile/provider key."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self._providers: dict[str, EmbeddingFn] = {}

    def register(self, key: str, fn: EmbeddingFn) -> None:
        """Execute register."""
        self._providers[key] = fn

    def get(self, key: str) -> EmbeddingFn:
        """Execute get."""
        if key not in self._providers:
            raise KeyError(f"Unknown embedding provider: {key}")
        return self._providers[key]

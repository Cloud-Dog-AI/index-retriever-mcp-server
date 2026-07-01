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

"""Discovery cache backed by cloud_dog_cache."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from cloud_dog_cache import CacheConfig, CacheManager, cache_key, get_cache_manager


class ServiceDiscoveryCache:
    """300-second default discovery cache for MCP tools and A2A agent cards."""

    def __init__(self, *, ttl_seconds: int = 300, manager: CacheManager | None = None) -> None:
        """Initialise the discovery cache using the platform cache package."""
        self.ttl_seconds = max(1, int(ttl_seconds))
        self._manager = manager or get_cache_manager() or CacheManager(
            CacheConfig(enabled=True, backend="memory", ttl_seconds=self.ttl_seconds, max_entries=512)
        )

    async def get_or_fetch(
        self,
        namespace: str,
        service_name: str,
        fetcher: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Return a cached discovery payload or fetch and cache it."""
        key = cache_key(
            "index-retriever.outbound.discovery",
            params={"namespace": namespace, "service_name": service_name},
        )
        cached = await self._manager.get(key)
        if cached is not None:
            return cached
        value = await fetcher()
        await self._manager.set(key, value, ttl=self.ttl_seconds, tags=("outbound-discovery", service_name))
        return value


def extract_agent_skills(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract a normalized skill list from a PS-72 agent card shape."""
    candidates: list[Any] = []
    for key in ("skills", "tools"):
        value = card.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    capabilities = card.get("capabilities")
    if isinstance(capabilities, dict) and isinstance(capabilities.get("skills"), list):
        candidates.extend(capabilities["skills"])

    skills: list[dict[str, Any]] = []
    for item in candidates:
        if isinstance(item, dict):
            skill_id = str(item.get("id") or item.get("name") or "").strip()
            if skill_id:
                skills.append(
                    {
                        "id": skill_id,
                        "name": str(item.get("name") or skill_id),
                        "description": str(item.get("description") or ""),
                    }
                )
        elif isinstance(item, str) and item.strip():
            skills.append({"id": item.strip(), "name": item.strip(), "description": ""})
    return skills

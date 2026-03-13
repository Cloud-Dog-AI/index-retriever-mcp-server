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

# index-retriever-mcp-server — Collection Manager
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Collection management using cloud_dog_vdb adapters.

from __future__ import annotations

from index_tools.vdb.adapters import InMemoryVdbAdapter


class CollectionManager:
    """Collection management facade for VDB operations."""

    def __init__(self, adapter: InMemoryVdbAdapter | None = None) -> None:
        """Initialise the instance state."""
        self.adapter = adapter or InMemoryVdbAdapter()

    def create(self, name: str) -> None:
        """Execute create."""
        self.adapter.create_collection(name)

    def list(self) -> list[str]:
        """Execute list."""
        return self.adapter.list_collections()

    def delete(self, name: str) -> None:
        """Execute delete."""
        self.adapter.delete_collection(name)

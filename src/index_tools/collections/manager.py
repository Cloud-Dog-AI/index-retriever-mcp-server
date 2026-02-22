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

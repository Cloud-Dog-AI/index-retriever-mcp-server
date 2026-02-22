# index-retriever-mcp-server — UT1.24
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests VDB registry lookup.

from index_tools.vdb.adapters import InMemoryVdbAdapter
from index_tools.vdb.registry import VdbRegistry


def test_vdb_registry_lookup() -> None:
    registry = VdbRegistry()
    registry.register("chroma", InMemoryVdbAdapter)
    adapter = registry.get("chroma")
    assert isinstance(adapter, InMemoryVdbAdapter)

# index-retriever-mcp-server — ST1.6
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local top_k search behaviour.

from tests.local_runtime import LocalIndexRuntime


def test_search_top_k(local_service: LocalIndexRuntime) -> None:
    for i in range(4):
        local_service.ingest_text("default", "st_topk", f"shared token {i}", f"api://topk/{i}", actor="system")
    rows = local_service.search("default", "st_topk", "shared", top_k=2)
    assert len(rows) == 2

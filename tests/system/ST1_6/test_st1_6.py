# index-retriever-mcp-server — ST1.6
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live top_k search behaviour.

from tests.live_runtime import LiveIndexRuntime


def test_search_top_k(live_service: LiveIndexRuntime) -> None:
    for i in range(4):
        live_service.ingest_text("default", "st_topk", f"shared token {i}", f"api://topk/{i}", actor="system")
    rows = live_service.search("default", "st_topk", "shared", top_k=2)
    assert len(rows) == 2

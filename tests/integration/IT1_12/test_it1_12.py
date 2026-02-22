# index-retriever-mcp-server — IT1.12
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Streaming ingest ordering over live runtime.

from tests.live_runtime import LiveIndexRuntime


def test_streaming_ingest_sse(live_service: LiveIndexRuntime) -> None:
    session_id = live_service.ingest_stream_open("default", "it_stream", ordering_key="thread-9")
    j1 = live_service.ingest_stream_event(session_id, "first event", actor="integration")
    j2 = live_service.ingest_stream_event(session_id, "second event", actor="integration")
    closed = live_service.ingest_stream_close(session_id)
    assert closed["job_ids"] == [j1, j2]
    assert closed["ingested_events"] == 2

# index-retriever-mcp-server — AT1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live idempotent ingest workflow.

from tests.live_runtime import LiveIndexRuntime


def test_full_workflow_deduplicate_skip(live_service: LiveIndexRuntime) -> None:
    key = "at-idempotent-key"
    first = live_service.ingest_text(
        "default",
        "at_dedupe",
        "dedupe text",
        "api://at/dedupe",
        actor="application",
        idempotency_key=key,
    )
    second = live_service.ingest_text(
        "default",
        "at_dedupe",
        "dedupe text",
        "api://at/dedupe",
        actor="application",
        idempotency_key=key,
    )
    assert first.job_id == second.job_id

# index-retriever-mcp-server — AT1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live profile and collection lifecycle workflow.

from tests.live_runtime import LiveIndexRuntime


def test_full_workflow_profile_collection_lifecycle(live_service: LiveIndexRuntime) -> None:
    live_service.admin_profile_create("at_profile", roles={"admin"})
    live_service.admin_collection_create("at_profile", "ledger", roles={"admin"})

    _ = live_service.ingest_text(
        "at_profile",
        "ledger",
        "invoice ledger record",
        "api://at/ledger",
        actor="application",
    )
    assert live_service.search("at_profile", "ledger", "invoice")

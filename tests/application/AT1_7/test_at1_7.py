# index-retriever-mcp-server — AT1.7
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Multi-profile cross-backend parity with metadata invariants.

from tests.live_runtime import LiveIndexRuntime


def test_multi_profile_cross_backend_metadata_parity(live_service: LiveIndexRuntime) -> None:
    providers = ["chroma", "qdrant"]
    if "infinity" in live_service._enabled_providers and live_service.backend_health_check(provider_id="infinity"):
        providers.append("infinity")

    invariants: list[tuple[str, str, str]] = []
    for provider_id in providers:
        profile = f"at_profile_{provider_id}"
        collection = f"at_parity_{provider_id}"
        source_uri = f"file://application/parity/{provider_id}/document.txt"
        live_service.admin_profile_create(profile, roles={"admin"})
        _ = live_service.ingest_text(
            profile=profile,
            collection=collection,
            text=f"{provider_id} parity payload token",
            source=source_uri,
            actor="application",
            provider_id=provider_id,
            metadata={"document_id": f"AT1-7-{provider_id.upper()}"},
        )
        rows = live_service.search(
            profile,
            collection,
            "parity payload",
            provider_id=provider_id,
            filters={"document_id": f"AT1-7-{provider_id.upper()}"},
            top_k=3,
        )
        assert rows
        metadata = rows[0]["metadata"]
        invariants.append(
            (
                str(metadata.get("source_uri", "")),
                str(metadata.get("filename", "")),
                str(metadata.get("mime_type", "")),
            )
        )

    assert invariants
    assert all(item[1] == "document.txt" for item in invariants)
    assert all(item[2] == "text/plain" for item in invariants)

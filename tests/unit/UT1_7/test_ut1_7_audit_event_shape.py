# index-retriever-mcp-server — UT1.7
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests audit event shape.

from index_tools.audit.events import AuditEvent


def test_audit_event_shape() -> None:
    event = AuditEvent(actor="user", operation="ingest", profile="default", collection="kb")
    payload = event.model_dump()
    assert payload["actor"] == "user"
    assert payload["operation"] == "ingest"
    assert payload["timestamp_utc"] is not None

# index-retriever-mcp-server — UT1.8
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests audit secret redaction.

from index_tools.audit.logger import redact_payload


def test_audit_redaction() -> None:
    payload = {"api_key": "secret", "nested": {"password": "p"}, "ok": "yes"}
    redacted = redact_payload(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["ok"] == "yes"

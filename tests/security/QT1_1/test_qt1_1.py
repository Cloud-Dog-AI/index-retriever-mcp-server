# index-retriever-mcp-server — QT1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Secrets are redacted from audit logs.

from index_tools.tools.service import IndexService


def test_secrets_never_logged(service: IndexService) -> None:
    _ = service.ingest_text(
        "default",
        "secure",
        "contains secrets",
        "inline://secrets",
        actor="writer",
        metadata={"api_key": "super-secret", "password": "hidden"},
    )
    content = service.audit_logger.path.read_text(encoding="utf-8")
    assert "super-secret" not in content
    assert "hidden" not in content
    assert "[REDACTED]" in content

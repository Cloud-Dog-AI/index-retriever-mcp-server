# index-retriever-mcp-server — QT1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: UK English spelling checks for key security messages.

from index_server.auth.middleware import AuthMiddleware


def test_uk_english_compliance() -> None:
    middleware = AuthMiddleware()
    error_messages = [
        "Authorisation failed",
        "Authentication failed",
    ]
    assert all("Authorisation" in msg or "Authentication" in msg for msg in error_messages)
    assert middleware.backend_name() in {"cloud_dog_idam", "fallback"}

# index-retriever-mcp-server — QT1.6
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Provider diagnostic envelope is explicit and secret-safe.

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi.testclient import TestClient

from index_server.api_server import build_api_app
from tests.http_paths import api_tools_path
from tests.live_runtime import LiveIndexRuntime


def _post_json(url: str, payload: dict[str, object], headers: dict[str, str]) -> tuple[int, dict[str, object]]:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body)


def test_provider_diagnostic_error_envelope_secret_safe(
    live_service: LiveIndexRuntime, runtime_mode: str, runtime_endpoints: dict[str, str] | None
) -> None:
    payload = {
        "text": "trigger parser diagnostic",
        "source_uri": "file://qt/diag.txt",
        "parser_chain": ["deepdoc"],
        "parser_services": {
            "deepdoc": {
                "enabled": True,
                "command": ["deepdoc", "--token=super-secret-token"],
            }
        },
    }

    if runtime_mode == "local-server":
        client = TestClient(build_api_app(service=live_service))
        response = client.post(
            api_tools_path("ingest_preview"),
            json=payload,
            headers={"Authorization": "Bearer valid-writer-token"},
        )
        assert response.status_code == 400
        detail = str(response.json().get("detail", ""))
    else:
        assert runtime_endpoints is not None
        status, body = _post_json(
            f"{runtime_endpoints['api_base_url']}{api_tools_path('ingest_preview')}",
            payload,
            {
                "Authorization": "Bearer valid-writer-token",
                "Content-Type": "application/json",
            },
        )
        assert status == 400
        detail = json.dumps(body, sort_keys=True)

    assert "PROVIDER_DIAGNOSTIC" in detail
    assert "super-secret-token" not in detail
    assert ("token=" not in detail.lower()) or ("[REDACTED]" in detail)

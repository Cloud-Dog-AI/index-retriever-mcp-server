from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

MONOREPO_ROOT = Path('/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo')
MONOREPO_APP = MONOREPO_ROOT / 'apps' / 'index-retriever'
PLAYWRIGHT_BIN = MONOREPO_ROOT / 'node_modules' / '.bin' / 'playwright'
PLAYWRIGHT_CONFIG = Path('/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server/tests/application/webui_playwright.config.ts')
NODE_PATH = os.pathsep.join(
    [
        str(MONOREPO_ROOT / 'node_modules'),
        str(MONOREPO_APP / 'node_modules'),
    ]
)


def _read_port(name: str, default: int) -> int:
    raw = os.environ.get(name, '').strip()
    if not raw:
        return default
    return int(raw)


def _http_status(url: str) -> int:
    request = Request(url, method='GET')
    with urlopen(request, timeout=5) as response:
        return int(getattr(response, 'status', 0) or 0)


def ensure_runtime_ready() -> tuple[str, str]:
    api_port = _read_port('CLOUD_DOG__API_SERVER__PORT', 8074)
    web_port = _read_port('CLOUD_DOG__WEB_SERVER__PORT', 8075)
    api_url = f'http://127.0.0.1:{api_port}'
    web_url = f'http://127.0.0.1:{web_port}'
    checks = [
        (f'{api_url}/health', 200),
        (f'{web_url}/login', 200),
    ]
    deadline = time.time() + 30.0
    last_error = ''
    while time.time() < deadline:
        all_ready = True
        for url, expected in checks:
            try:
                status = _http_status(url)
            except URLError as exc:  # pragma: no cover - runtime failure path
                all_ready = False
                last_error = f'WebUI runtime not reachable at {url}: {exc}'
                break
            if status != expected:
                all_ready = False
                last_error = f'WebUI runtime returned {status} for {url}, expected {expected}'
                break
        if all_ready:
            return web_url, api_url
        time.sleep(1.0)
    pytest.fail(last_error or 'WebUI runtime did not become ready in time')


def run_playwright_spec(spec_name: str) -> None:
    web_url, api_url = ensure_runtime_ready()
    env = os.environ.copy()
    env['NODE_PATH'] = NODE_PATH
    env['E2E_BASE_URL'] = web_url
    env['E2E_API_BASE_URL'] = api_url
    env['E2E_API_KEY'] = env.get('E2E_API_KEY', 'valid-admin-token')
    command = [
        str(PLAYWRIGHT_BIN),
        'test',
        '--config',
        str(PLAYWRIGHT_CONFIG),
        spec_name,
    ]
    completed = subprocess.run(
        command,
        cwd=str(MONOREPO_APP),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f'Playwright failed for {spec_name}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}'
        )

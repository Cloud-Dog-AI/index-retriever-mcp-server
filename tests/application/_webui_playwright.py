from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from threading import Lock
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
from tests.http_paths import api_tools_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MONOREPO_ROOT = PROJECT_ROOT.parent / 'ui'
if not (_DEFAULT_MONOREPO_ROOT / 'apps' / 'index-retriever').is_dir():
    _DEFAULT_MONOREPO_ROOT = Path('/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo')
MONOREPO_ROOT = Path(
    os.environ.get('INDEX_RETRIEVER_UI_MONOREPO', str(_DEFAULT_MONOREPO_ROOT))
).resolve()
MONOREPO_APP = MONOREPO_ROOT / 'apps' / 'index-retriever'
PLAYWRIGHT_BIN = MONOREPO_ROOT / 'node_modules' / '.bin' / 'playwright'
PLAYWRIGHT_CONFIG = MONOREPO_APP / 'playwright.config.ts'
NODE_PATH = os.pathsep.join(
    [
        str(MONOREPO_ROOT / 'node_modules'),
        str(MONOREPO_APP / 'node_modules'),
    ]
)
SERVER_CONTROL = PROJECT_ROOT / 'server_control.sh'
_RUNTIME_BOOT_LOCK = Lock()
_TEST_API_KEYS = 'test-api-key,valid-reader-token:reader,valid-writer-token:writer,valid-admin-token:admin'


def _api_admin_token() -> str:
    return os.environ.get('E2E_API_KEY', 'valid-admin-token').strip() or 'valid-admin-token'


def _env_file_for_runtime() -> str:
    configured = os.environ.get('CLOUD_DOG_ENV_FILES', '').strip()
    if configured:
        return configured.split(os.pathsep, 1)[0]
    tier = os.environ.get('TEST_ENV_TIER', '').strip().upper() or 'AT'
    return str(PROJECT_ROOT / 'tests' / f'env-{tier}')


def _read_port(name: str, default: int) -> int:
    raw = os.environ.get(name, '').strip()
    if not raw:
        return default
    return int(raw)


def _web_login_credentials() -> tuple[str, str]:
    username = (
        os.environ.get('E2E_WEB_LOGIN_USERNAME', '').strip()
        or os.environ.get('CLOUD_DOG__WEB_LOGIN__USERNAME', '').strip()
        or os.environ.get('CLOUD_DOG_WEB_LOGIN_USERNAME', '').strip()
        or 'admin'
    )
    password = (
        os.environ.get('E2E_WEB_LOGIN_PASSWORD', '').strip()
        or os.environ.get('CLOUD_DOG__WEB_LOGIN__PASSWORD', '').strip()
        or os.environ.get('CLOUD_DOG_WEB_LOGIN_PASSWORD', '').strip()
        or 'OrangeRiverTable'
    )
    return username, password


def _http_status(url: str) -> int:
    status, _, _ = _http_response(url, timeout=5.0)
    return status


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _http_response(
    url: str,
    *,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
    timeout: float = 5.0,
) -> tuple[int, str, str]:
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    request = Request(
        url,
        data=body,
        headers={str(key): str(value) for key, value in (headers or {}).items()},
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, 'status', 0) or 0)
            return (
                status,
                response.read().decode('utf-8', errors='replace'),
                response.headers.get_content_type(),
            )
    except HTTPError as exc:
        body_text = exc.read().decode('utf-8', errors='replace')
        content_type = exc.headers.get_content_type() if exc.headers is not None else ''
        return exc.code, body_text, content_type


def _http_json(
    url: str,
    *,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
    timeout: float = 5.0,
) -> tuple[int, str]:
    status, body, _ = _http_response(
        url,
        method=method,
        headers=headers,
        payload=payload,
        timeout=timeout,
    )
    return status, body


def _is_shutdown_payload(body: str) -> bool:
    text = body.strip()
    if not text:
        return False
    return 'Service is shutting down' in text


def _is_html_document(body: str) -> bool:
    text = body.lstrip().lower()
    return text.startswith('<!doctype html') or text.startswith('<html')


def _warm_collection_admin_flow(api_url: str) -> None:
    token = _api_admin_token()
    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {token}',
        'x-api-key': token,
    }
    collection = f'warmup-{int(time.time() * 1000)}'
    payload = {
        'profile': 'default',
        'collection': collection,
        'description': 'warmup',
        'dimensions': 1024,
        'distance_metric': 'cosine',
        'allowed_roles': ['reader', 'writer', 'maintainer', 'admin'],
        'metadata': {'warmup': True},
    }
    create_status, create_body = _http_json(
        f'{api_url}{api_tools_path("admin_collection_create")}',
        method='POST',
        headers=headers,
        payload=payload,
        timeout=90.0,
    )
    if create_status != 200:
        raise AssertionError(
            f'Warmup create failed with status {create_status} for {collection}: {create_body}'
        )
    delete_status, delete_body = _http_json(
        f'{api_url}{api_tools_path("admin_collection_delete")}',
        method='POST',
        headers=headers,
        payload={'profile': 'default', 'collection': collection},
        timeout=30.0,
    )
    if delete_status != 200:
        raise AssertionError(
            f'Warmup delete failed with status {delete_status} for {collection}: {delete_body}'
        )


def _restart_runtime_for_webui() -> None:
    env = os.environ.copy()
    # The WebUI runtime launched here via server_control.sh is a standalone,
    # production-style process — it is NOT executing under pytest. Leaking the
    # parent pytest's PYTEST_CURRENT_TEST into the child forces
    # api_server._maybe_disable_timeout_middleware() down its "in pytest"
    # branch, which materialises the middleware stack early; the subsequent
    # @app.middleware("http") auth-before-validation registration (W28R-3001)
    # then raises "Cannot add middleware after an application has started" and
    # the API server never binds. Strip the marker so the child boots exactly
    # like the deployed dev-tier runtime.
    env.pop('PYTEST_CURRENT_TEST', None)
    web_username, web_password = _web_login_credentials()
    api_port = _read_port('CLOUD_DOG__API_SERVER__PORT', 8074)
    api_base_url = f'http://127.0.0.1:{api_port}'
    env['CLOUD_DOG__WEB_LOGIN__USERNAME'] = web_username
    env['CLOUD_DOG_WEB_LOGIN_USERNAME'] = web_username
    env['CLOUD_DOG__WEB_LOGIN__PASSWORD'] = web_password
    env['CLOUD_DOG_WEB_LOGIN_PASSWORD'] = web_password
    env['CLOUD_DOG__INDEX__UI__AUTH_MODE'] = 'cookie'
    env['CLOUD_DOG__INDEX__UI__API_BASE_URL'] = api_base_url
    env['CLOUD_DOG__INDEX__AUTH__API_KEYS'] = env.get('CLOUD_DOG__INDEX__AUTH__API_KEYS', _TEST_API_KEYS) or _TEST_API_KEYS
    env['E2E_API_KEY'] = env.get('E2E_API_KEY', _api_admin_token()) or _api_admin_token()

    stop_completed = subprocess.run(
        [str(SERVER_CONTROL), '--env', _env_file_for_runtime(), 'stop', 'all'],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    web_port = _read_port('CLOUD_DOG__WEB_SERVER__PORT', 8075)
    drain_deadline = time.time() + 30.0
    while time.time() < drain_deadline:
        if not _port_open('127.0.0.1', api_port) and not _port_open('127.0.0.1', web_port):
            break
        time.sleep(0.5)
    start_completed = subprocess.run(
        [str(SERVER_CONTROL), '--env', _env_file_for_runtime(), 'start', 'all'],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if start_completed.returncode != 0 and 'web: failed to start' in (
        f'{start_completed.stdout}\n{start_completed.stderr}'
    ):
        time.sleep(2.0)
        start_completed = subprocess.run(
            [str(SERVER_CONTROL), '--env', _env_file_for_runtime(), 'start', 'web'],
            cwd=str(PROJECT_ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    if start_completed.returncode != 0:
        raise AssertionError(
            'Failed to restart local runtime for Playwright\n'
            f'STOP STDOUT:\n{stop_completed.stdout}\n'
            f'STOP STDERR:\n{stop_completed.stderr}\n'
            f'START STDOUT:\n{start_completed.stdout}\n'
            f'START STDERR:\n{start_completed.stderr}'
        )


def ensure_runtime_ready() -> tuple[str, str]:
    api_port = _read_port('CLOUD_DOG__API_SERVER__PORT', 8074)
    web_port = _read_port('CLOUD_DOG__WEB_SERVER__PORT', 8075)
    api_url = f'http://127.0.0.1:{api_port}'
    web_url = f'http://127.0.0.1:{web_port}'
    deadline = time.time() + 90.0
    last_error = ''
    consecutive_ready = 0
    with _RUNTIME_BOOT_LOCK:
        _restart_runtime_for_webui()
    while time.time() < deadline:
        try:
            api_status, api_body, _ = _http_response(f'{api_url}/health', timeout=10.0)
            if api_status != 200:
                consecutive_ready = 0
                last_error = f'WebUI runtime returned {api_status} for {api_url}/health: {api_body}'
                time.sleep(1.0)
                continue

            login_status, login_body, login_content_type = _http_response(f'{web_url}/login', timeout=10.0)
            if login_status != 200:
                consecutive_ready = 0
                last_error = f'WebUI runtime returned {login_status} for {web_url}/login'
                time.sleep(1.0)
                continue
            if _is_shutdown_payload(login_body):
                consecutive_ready = 0
                last_error = f'WebUI login served shutdown payload: {login_body}'
                time.sleep(1.0)
                continue
            if not _is_html_document(login_body):
                consecutive_ready = 0
                last_error = (
                    f'WebUI login did not serve SPA HTML (content-type {login_content_type}): '
                    f'{login_body[:200]}'
                )
                time.sleep(1.0)
                continue

            runtime_status, runtime_body, _ = _http_response(f'{web_url}/runtime-config.js', timeout=10.0)
            if runtime_status != 200 or 'window.__RUNTIME_CONFIG__' not in runtime_body:
                consecutive_ready = 0
                last_error = (
                    f'WebUI runtime config not ready: status={runtime_status} body={runtime_body[:200]}'
                )
                time.sleep(1.0)
                continue

            try:
                _warm_collection_admin_flow(api_url)
            except AssertionError as exc:
                consecutive_ready = 0
                last_error = str(exc)
                time.sleep(1.0)
                continue

            token = _api_admin_token()
            auth_headers = {
                'accept': 'application/json',
                'authorization': f'Bearer {token}',
                'x-api-key': token,
            }
            status_code, status_body = _http_json(f'{web_url}/status', headers=auth_headers, timeout=10.0)
            if status_code != 200:
                consecutive_ready = 0
                last_error = f'WebUI status returned {status_code}: {status_body[:200]}'
                time.sleep(1.0)
                continue
            if _is_shutdown_payload(status_body):
                consecutive_ready = 0
                last_error = f'WebUI status still reports shutdown: {status_body}'
                time.sleep(1.0)
                continue

            consecutive_ready += 1
            if consecutive_ready >= 2:
                return web_url, api_url
        except URLError as exc:
            consecutive_ready = 0
            last_error = f'WebUI runtime not reachable: {exc}'
        time.sleep(1.0)
    pytest.fail(last_error or 'WebUI runtime did not become ready in time')


def run_playwright_spec(spec_name: str) -> None:
    web_url, api_url = ensure_runtime_ready()
    env = os.environ.copy()
    web_username, web_password = _web_login_credentials()
    env['NODE_PATH'] = NODE_PATH
    env['E2E_BASE_URL'] = web_url
    env['E2E_API_BASE_URL'] = api_url
    env['E2E_API_KEY'] = env.get('E2E_API_KEY', _api_admin_token()) or _api_admin_token()
    env['E2E_AUTH_MODE'] = 'cookie'
    env['E2E_USE_RUNTIME_INJECTION'] = '1'
    env['E2E_WEB_LOGIN_USERNAME'] = web_username
    env['E2E_WEB_LOGIN_PASSWORD'] = web_password
    env['E2E_USE_EXISTING_SERVER'] = '1'
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

# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# index-retriever-mcp-server — Shared Test Fixtures
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Pytest fixtures enforcing env selection and env file loading.

from __future__ import annotations

import os
import re
import socket
import sys
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pytest
from cloud_dog_config.compiler.vault_resolver import resolve_vault_identifier
from cloud_dog_config.vault.client import VaultClient, VaultConnectionConfig

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from index_server.auth.middleware import AuthMiddleware  # noqa: E402
from index_tools.tools.service import IndexService  # noqa: E402
from tests.live_runtime import LiveIndexRuntime, load_vault_dev_config  # noqa: E402

_INITIAL_ENV_KEYS = set(os.environ.keys())
_LIVE_REQUIRED_TIERS = {"ST", "IT", "AT", "CT", "QT"}
_RUNTIME_MODES = {"local-server", "local-docker", "remote-runtime"}
_EXTERNAL_ENDPOINT_MODES = {"local-docker", "remote-runtime"}
_VAULT_REF_PATTERN = re.compile(r"^\$\{(vault\.[^}]+)\}$")


@lru_cache(maxsize=1)
def _vault_client() -> VaultClient | None:
    addr = os.environ.get("VAULT_ADDR", "").strip()
    token = os.environ.get("VAULT_TOKEN", "").strip()
    if not addr or not token:
        return None
    mount = os.environ.get("VAULT_MOUNT_POINT", "").strip().strip("/")
    config_path = os.environ.get("VAULT_CONFIG_PATH", "").strip().strip("/")
    if config_path:
        mount = "/".join([p for p in (mount, config_path) if p])
    try:
        return VaultClient(
            VaultConnectionConfig(
                server=addr,
                token=token,
                timeout_seconds=10.0,
                mount_point=mount,
            )
        )
    except Exception:
        return None


def _resolve_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return value
    match = _VAULT_REF_PATTERN.match(value)
    if match is None:
        return value
    client = _vault_client()
    if client is None:
        return value
    resolved = resolve_vault_identifier(match.group(1), vault=client)
    if isinstance(resolved, (str, int, float, bool)):
        resolved_text = str(resolved).strip()
        if resolved_text:
            return resolved_text
    return value


def _load_env_file(path: Path, *, override: bool) -> dict[str, str]:
    """Load KEY=VALUE pairs from an env file into process environment."""
    loaded: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in _INITIAL_ENV_KEYS:
            loaded[key] = os.environ[key]
            continue
        if not override and key in os.environ:
            loaded[key] = os.environ[key]
            continue
        resolved = _resolve_env_value(value)
        os.environ[key] = resolved
        loaded[key] = resolved
    return loaded


def _connect_endpoint(label: str, raw_url: str) -> str:
    """Validate socket capability and endpoint health for runtime HTTP endpoints."""
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.hostname:
        pytest.fail(f"Invalid {label} URL: {raw_url}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    sock = socket.socket()
    sock.settimeout(5)
    try:
        sock.connect((parsed.hostname, port))
    except PermissionError as exc:
        pytest.fail(f"BLOCKED: socket capability restricted for {label} {parsed.hostname}:{port}: {exc}")
    except OSError as exc:
        if getattr(exc, "errno", None) == 1:
            pytest.fail(f"BLOCKED: socket capability restricted for {label} {parsed.hostname}:{port}: {exc}")
        pytest.fail(f"{label} endpoint is not reachable at {parsed.hostname}:{port}: {exc}")
    finally:
        sock.close()

    health_url = f"{raw_url.rstrip('/')}/health"
    req = Request(health_url, method="GET")
    try:
        with urlopen(req, timeout=10) as response:
            status = int(getattr(response, "status", 0) or 0)
        if status != 200:
            pytest.fail(f"{label} health check failed at {health_url}: HTTP {status}")
    except (HTTPError, URLError, TimeoutError) as exc:
        pytest.fail(f"{label} health check failed at {health_url}: {exc}")
    return raw_url.rstrip("/")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add mandatory --env option for test environment selection."""
    with suppress(ValueError):
        parser.addoption(
            "--env",
            action="append",
            required=True,
            help=("Test environment(s). Use UT/ST/IT/AT/QT, tests/env-<TIER>, or private/env-<name>."),
        )


@pytest.fixture(scope="session")
def runtime_mode(load_env_files: dict[str, str]) -> str:
    """Resolve and validate runtime mode contract for matrix execution."""
    _ = load_env_files
    raw_mode = os.environ.get("INDEX_RETRIEVER_RUNTIME_MODE", "local-server").strip().lower()
    if raw_mode not in _RUNTIME_MODES:
        raise pytest.UsageError(
            f"Invalid INDEX_RETRIEVER_RUNTIME_MODE={raw_mode!r}. Expected one of: {', '.join(sorted(_RUNTIME_MODES))}."
        )
    return raw_mode


@pytest.fixture(scope="session")
def runtime_endpoints(runtime_mode: str) -> dict[str, str] | None:
    """Provide validated runtime API/MCP endpoints for external runtime modes."""
    if runtime_mode not in _EXTERNAL_ENDPOINT_MODES:
        return None

    api_base = os.environ.get("INDEX_RETRIEVER_API_BASE_URL", "").strip()
    mcp_base = os.environ.get("INDEX_RETRIEVER_MCP_BASE_URL", "").strip()
    if not api_base or not mcp_base:
        pytest.fail("External runtime mode requires INDEX_RETRIEVER_API_BASE_URL and INDEX_RETRIEVER_MCP_BASE_URL.")

    return {
        "api_base_url": _connect_endpoint("API", api_base),
        "mcp_base_url": _connect_endpoint("MCP", mcp_base),
    }


@pytest.fixture(scope="session")
def env_args(request: pytest.FixtureRequest) -> list[str]:
    """Return raw --env arguments preserving input order and uniqueness."""
    values = request.config.getoption("--env")
    if isinstance(values, str):
        items = [values]
    elif isinstance(values, list):
        items = values
    else:
        items = []

    seen: set[str] = set()
    resolved: list[str] = []
    for item in items:
        candidate = item.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        resolved.append(candidate)
    return resolved


@pytest.fixture(scope="session")
def env_tiers(env_args: list[str], load_env_files: dict[str, str]) -> list[str]:
    """Return canonical env tiers for convenience fixtures."""
    _ = load_env_files
    tiers: list[str] = []
    for arg in env_args:
        name = Path(arg).name
        token = name.removeprefix("env-") if name.startswith("env-") else arg
        tiers.append(token.upper())
    from_env = os.environ.get("TEST_ENV_TIER", "").strip().upper()
    if from_env and from_env not in tiers:
        tiers.append(from_env)
    return tiers


@pytest.fixture(scope="session", autouse=True)
def load_env_files(env_args: list[str]) -> dict[str, str]:
    """Load env files from tests/env-* with optional private overlays."""
    loaded: dict[str, str] = {}
    tests_dir = Path(__file__).parent

    # Baseline .env defaults (without overriding existing process env).
    root_env = ROOT / ".env"
    if root_env.exists() and root_env.is_file():
        loaded.update(_load_env_file(root_env, override=False))
    root_env_local = ROOT / ".env.local"
    if root_env_local.exists() and root_env_local.is_file():
        loaded.update(_load_env_file(root_env_local, override=False))

    for arg in env_args:
        candidate = arg.strip()
        if not candidate:
            continue

        candidates: list[Path] = []
        token = candidate.upper()
        if token in {"UT", "ST", "IT", "AT", "QT"}:
            candidates.append(tests_dir / f"env-{token}")
        else:
            explicit = (ROOT / candidate).resolve()
            if explicit.exists() and explicit.is_file():
                candidates.append(explicit)
            else:
                name = Path(candidate).name
                if not name.startswith("env-"):
                    name = f"env-{name}"
                candidates.append(tests_dir / name)
                candidates.append(ROOT / "private" / name)

        base_loaded = False
        for env_path in candidates:
            if env_path.exists() and env_path.is_file():
                loaded.update(_load_env_file(env_path, override=True))
                base_loaded = True
                break
        if not base_loaded:
            raise pytest.UsageError(f"Env file not found for --env {candidate}")

        # Optional private overlays (environment-specific external details/secrets).
        base_name = env_path.name
        overlay_candidates = [
            ROOT / "private" / f"{base_name}-secrets",
            ROOT / "private" / f"{base_name}-external",
            ROOT / "private" / f"{base_name}-local",
        ]
        for overlay in overlay_candidates:
            if overlay.exists() and overlay.is_file():
                loaded.update(_load_env_file(overlay, override=True))

    return loaded


@pytest.fixture(scope="session")
def env(env_tiers: list[str]) -> str:
    """Provide backwards-compatible single-env fixture."""
    if not env_tiers:
        return ""
    return env_tiers[0]


@pytest.fixture()
def service(tmp_path: Path) -> IndexService:
    """Provide a per-test in-memory index service."""
    audit_path = tmp_path / "audit.jsonl"
    return IndexService(audit_path=str(audit_path))


@pytest.fixture()
def auth() -> AuthMiddleware:
    """Provide auth middleware with deterministic local credentials."""
    return AuthMiddleware(api_keys={"test-api-key": {"admin", "maintainer", "writer", "reader"}})


@pytest.fixture(scope="session")
def live_vault_dev_config() -> dict[str, object]:
    """Provide live Vault dev configuration if Vault env is available."""
    return load_vault_dev_config(required=False)


@pytest.fixture(scope="session")
def live_service_preflight(env_tiers: list[str]) -> None:
    """Validate live backend readiness once per session before live-tier tests."""
    active_live_tiers = [tier for tier in env_tiers if tier in _LIVE_REQUIRED_TIERS]
    tier_label = ",".join(active_live_tiers) if active_live_tiers else (env_tiers[0] if env_tiers else "UNKNOWN")

    if "VAULT_TOKEN" not in _INITIAL_ENV_KEYS or not os.environ.get("VAULT_TOKEN"):
        pytest.fail(
            f"Live runtime environment is not configured for {tier_label} tier: missing VAULT_TOKEN. "
            "Run: set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a"
        )

    try:
        runtime = LiveIndexRuntime()
    except Exception as exc:
        pytest.fail(
            f"Live runtime environment is not configured for {tier_label} tier: {exc}. "
            "Run: set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a"
        )

    try:
        issues = runtime.preflight()
    finally:
        runtime.cleanup()

    if issues:
        pytest.fail(f"Live runtime dependencies not ready for {tier_label} tier: " + "; ".join(issues))


@pytest.fixture()
def live_service(live_service_preflight: None) -> LiveIndexRuntime:
    """Provide live runtime backed by env/Vault-configured services."""
    _ = live_service_preflight
    runtime = LiveIndexRuntime()
    try:
        yield runtime
    finally:
        runtime.cleanup()


@pytest.fixture(scope="session", autouse=True)
def live_service_cleanup_verification(env_tiers: list[str]) -> None:
    """Fail live-tier sessions if runtime collections are orphaned after test completion."""
    active_live_tiers = [tier for tier in env_tiers if tier in _LIVE_REQUIRED_TIERS]
    if not active_live_tiers:
        yield
        return
    if not os.environ.get("VAULT_TOKEN"):
        # ST/IT/AT/QT/CT no-vault runs intentionally fail earlier in preflight.
        yield
        return

    yield

    runtime: LiveIndexRuntime | None = None
    try:
        runtime = LiveIndexRuntime()
        orphans: list[str] = []
        for provider_id in sorted(runtime._enabled_providers):
            for name in runtime.list_run_collections(provider_id):
                orphans.append(f"{provider_id}:{name}")
                with suppress(Exception):
                    runtime._run(runtime.vdb_client.delete_collection(name, provider_id=provider_id))
        if orphans:
            prefix = LiveIndexRuntime.run_prefix() or "<unset>"
            pytest.fail(
                f"Live runtime cleanup left orphan collections for this session (prefix={prefix}): {', '.join(orphans)}"
            )
    finally:
        if runtime is not None:
            runtime.cleanup()

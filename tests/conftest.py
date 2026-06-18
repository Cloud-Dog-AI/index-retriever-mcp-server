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

from __future__ import annotations

import os
import re
import socket
import sys
from collections.abc import Iterator
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
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
from tests.live_runtime import LiveIndexRuntime, load_vault_dev_config, resolve_live_runtime_config  # noqa: E402

_INITIAL_ENV_KEYS = set(os.environ.keys())
_LIVE_REQUIRED_TIERS = {"ST", "IT", "AT", "CT", "QT"}
_RUNTIME_MODES = {"local-server", "local-docker", "remote-runtime"}
_EXTERNAL_ENDPOINT_MODES = {"local-docker", "remote-runtime"}
_VAULT_REF_PATTERN = re.compile(r"^\$\{(vault\.[^}]+)\}$")


def _ensure_test_run_prefix() -> str:
    token = os.environ.get("INDEX_RETRIEVER_TEST_RUN_PREFIX", "").strip().lower()
    if not token:
        token = f"r{uuid4().hex[:8]}"
        os.environ["INDEX_RETRIEVER_TEST_RUN_PREFIX"] = token
    # Service now reads index.test_run_prefix via cloud_dog_config (RULES §1.4.1);
    # export the config-path override so the test prefix reaches the service.
    os.environ["CLOUD_DOG__INDEX__TEST_RUN_PREFIX"] = token
    return token


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
    try:
        from tests.live_runtime import load_vault_dev_config  # noqa: WPS433

        dev_config = load_vault_dev_config(required=False)
        if dev_config:
            current: object = dev_config
            path_parts = match.group(1).split(".")
            for part in path_parts[2:] if path_parts[:2] == ["vault", "dev"] else path_parts[1:]:
                if not isinstance(current, dict) or part not in current:
                    current = None
                    break
                current = current[part]
            if isinstance(current, (str, int, float, bool)):
                resolved_text = str(current).strip()
                if resolved_text:
                    return resolved_text
    except Exception:
        pass
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

    if os.environ.get("TEST_ENV_TIER", "").strip().upper() in _LIVE_REQUIRED_TIERS:
        loaded["INDEX_RETRIEVER_TEST_RUN_PREFIX"] = _ensure_test_run_prefix()

    return loaded


@pytest.fixture(scope="session")
def env(env_tiers: list[str]) -> str:
    """Provide backwards-compatible single-env fixture."""
    if not env_tiers:
        return ""
    return env_tiers[0]


def _install_ut_embedding_mock() -> None:
    """W28A-323: Replace OllamaEmbeddingProvider.embed with a deterministic
    SHA256-based mock so UT tests never hit live Ollama endpoints.

    Applied once at module load when TEST_ENV_TIER=UT.
    """
    from hashlib import sha256

    async def _hash_embed(self: Any, text: str) -> list[float]:
        # Produce a deterministic 768-dimension vector (nomic-embed-text size).
        digest = sha256(text.encode("utf-8")).digest()
        vec: list[float] = []
        for i in range(768):
            vec.append(round(digest[i % 32] / 255.0 + (i % 7) * 0.001, 6))
        return vec

    try:
        from cloud_dog_vdb.embeddings.providers import OllamaEmbeddingProvider, OpenAIEmbeddingProvider
        OllamaEmbeddingProvider.embed = _hash_embed  # type: ignore[assignment]
        OpenAIEmbeddingProvider.embed = _hash_embed  # type: ignore[assignment]
    except ImportError:
        pass

    try:
        import cloud_dog_vdb.embeddings.providers as _emb_providers
        _original_build = _emb_providers.build_embedding_provider

        def _mock_build(config: Any) -> Any:
            class _HashProv:
                async def embed(self, text: str) -> list[float]:
                    digest = sha256(text.encode("utf-8")).digest()
                    return [round(digest[i % 32] / 255.0 + (i % 7) * 0.001, 6) for i in range(768)]
            return _HashProv()

        _emb_providers.build_embedding_provider = _mock_build  # type: ignore[assignment]
    except (ImportError, AttributeError):
        pass

    # Also patch the Chroma adapter's _embed_text directly so already-
    # created adapter instances use the mock.
    try:
        from cloud_dog_vdb.adapters.chroma import ChromaAdapter

        async def _mock_embed_text(self: Any, text: str, dim: int) -> list[float]:
            digest = sha256(text.encode("utf-8")).digest()
            return [round(digest[i % 32] / 255.0 + (i % 7) * 0.001, 6) for i in range(dim)]

        async def _mock_embed_many(self: Any, texts: list, dim: int) -> list:
            return [await _mock_embed_text(self, t, dim) for t in texts]

        ChromaAdapter._embed_text = _mock_embed_text  # type: ignore[assignment]
        ChromaAdapter._embed_many = _mock_embed_many  # type: ignore[assignment]
    except (ImportError, AttributeError):
        pass


_ut_embedding_mock_installed = False


@pytest.fixture(scope="session", autouse=True)
def _install_embedding_mock_after_env_load() -> None:
    """W28A-323: install embedding mock AFTER the env file has been loaded,
    so TEST_ENV_TIER is available."""
    global _ut_embedding_mock_installed
    if _ut_embedding_mock_installed:
        return
    if os.environ.get("TEST_ENV_TIER", "").upper() == "UT":
        _install_ut_embedding_mock()
        _ut_embedding_mock_installed = True


@pytest.fixture()
def service(tmp_path: Path, _install_embedding_mock_after_env_load: None) -> Iterator[IndexService]:
    """Provide a per-test in-memory index service."""
    audit_path = tmp_path / "audit.jsonl"
    instance = IndexService(audit_path=str(audit_path))
    try:
        yield instance
    finally:
        instance.close()


@pytest.fixture()
def auth() -> AuthMiddleware:
    """Provide auth middleware from the active test env contract."""
    return AuthMiddleware()


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
    resolve_live_runtime_config.cache_clear()
    runtime = LiveIndexRuntime()
    try:
        yield runtime
    finally:
        runtime.cleanup()
        resolve_live_runtime_config.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def shutdown_platform_logging_before_pytest_exit() -> Iterator[None]:
    """Stop platform logging workers before pytest closes captured streams."""
    yield
    IndexService.close_all_instances()
    from index_server.logging_runtime import shutdown_platform_logging

    shutdown_platform_logging()


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


# ---------------------------------------------------------------------------
# PS-REQ-TEST-TRACE marker registration + enforcement
# See PS-REQ-TEST-TRACE v1.0 §6 — added by W28C-1715 functional compliance fix.
# ---------------------------------------------------------------------------

_PS_REQ_TIER_MARKERS = {"QT", "UT", "ST", "IT", "AT"}
_PS_REQ_SURFACE_MARKERS = {"api", "mcp", "a2a", "webui", "cli", "internal"}

_CANONICAL_MARKERS = [
    # Tier markers
    "UT: unit tests — in-process, no live services",
    "IT: integration tests — require live VDB / embedding providers",
    "ST: system tests — require a fully running index-retriever stack",
    "AT: application / acceptance tests — full end-to-end user workflows",
    "QT: quality / compliance tests — static analysis, package compliance",
    # Surface markers
    "mcp: tests exercising the MCP (Model Context Protocol) surface",
    "api: tests exercising the REST API surface",
    "a2a: tests exercising the A2A / agent-to-agent surface",
    "webui: tests exercising the web UI surface",
    "cli: tests exercising a command-line interface surface",
    "internal: tests targeting internal / non-public surfaces",
    # Traceability markers
    "req(*ids): bind test to one or more requirement IDs per PS-REQ-TEST-TRACE",
    "probe: mark test as an exploratory probe not yet bound to a requirement ID",
    # Supplementary markers
    "timeout(seconds): per-test wall-clock timeout limit",
    "slow: mark a test as slow-running (may be excluded from fast runs)",
    "llm: mark a test as requiring a live LLM provider endpoint",
    "negative: mark a test as deliberately exercising failure / error paths",
]


def pytest_configure(config: pytest.Config) -> None:
    """Register all canonical PS-REQ-TEST-TRACE markers to suppress PytestUnknownMarkWarning."""
    for marker_decl in _CANONICAL_MARKERS:
        config.addinivalue_line("markers", marker_decl)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """PS-REQ-TEST-TRACE marker enforcement — fail session on missing tier/surface/req markers."""
    import sys

    failures: list[str] = []
    for item in items:
        marker_names = {m.name for m in item.iter_markers()}
        is_probe = "probe" in marker_names
        if not (marker_names & _PS_REQ_TIER_MARKERS):
            failures.append(
                f"{item.nodeid}: missing @pytest.mark.<tier> (one of {sorted(_PS_REQ_TIER_MARKERS)}) "
                "per PS-REQ-TEST-TRACE §6"
            )
        if not (marker_names & _PS_REQ_SURFACE_MARKERS):
            failures.append(
                f"{item.nodeid}: missing @pytest.mark.<surface> (one of {sorted(_PS_REQ_SURFACE_MARKERS)}) "
                "per PS-REQ-TEST-TRACE §6"
            )
        if not is_probe:
            req_marker = item.get_closest_marker("req")
            if req_marker is None or not req_marker.args:
                failures.append(
                    f"{item.nodeid}: missing @pytest.mark.req('FR-NNN') per PS-REQ-TEST-TRACE §6 "
                    "(add @pytest.mark.probe to mark as orphan)"
                )
    if failures:
        msg = (
            "PS-REQ-TEST-TRACE marker enforcement failed for "
            + str(len(failures))
            + " test(s):\n  "
            + "\n  ".join(failures[:20])
        )
        if len(failures) > 20:
            msg += f"\n  ... and {len(failures) - 20} more"
        print(msg, file=sys.stderr)
        pytest.exit(msg, returncode=2)

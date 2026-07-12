"""W28A-295 / W28E-1878 (IR-23): profile loading + demo-profile gating.

W28E-1878 IR-23: demo/test profiles (multilang, Transparent Borders, NATO,
Ukraine) are NOT shipped in defaults.yaml. A clean production install lists only
the 'default' profile. The demo suite lives in the opt-in config/demo-profiles.yaml
and loads only when index.demo_profiles.enabled is truthy
(CLOUD_DOG__INDEX__DEMO_PROFILES__ENABLED=true) — for demo/dev/preprod use.
"""
import pytest

DEMO_ENABLED = "CLOUD_DOG__INDEX__DEMO_PROFILES__ENABLED"
DEMO_PATH = "CLOUD_DOG__INDEX__DEMO_PROFILES__PATH"

_DEMO_NAMES = {
    "multilang",
    "nato-doctrine",
    "ukraine-researcher",
    "transparent-borders-research",
    "transparent-borders-report-generation",
    "demo27-transparent-borders",
    "transparent-borders-report-generation-country-reports",
    "transparent-borders-report-generation-knowledge",
    "transparent-borders-report-generation-web-support",
}


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    monkeypatch.setenv("CLOUD_DOG__INDEX__VDB__PROVIDER", "chroma")
    monkeypatch.setenv("CLOUD_DOG__INDEX__EMBEDDING__MODEL", "nomic-embed-text")
    monkeypatch.setenv("CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("CLOUD_DOG__INDEX__AUTH__API_KEYS", "test-admin-key")
    # Default state: demo profiles OFF unless a test opts in.
    monkeypatch.delenv(DEMO_ENABLED, raising=False)
    monkeypatch.delenv(DEMO_PATH, raising=False)
    # Reset the cached runtime tree so per-test env overrides take effect.
    import index_tools.tools.service as svc_mod
    svc_mod._RUNTIME_TREE_CACHE = None
    yield
    svc_mod._RUNTIME_TREE_CACHE = None


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")
def test_shipped_defaults_carry_no_demo_profiles(tmp_path):
    """IR-23: with demo profiles OFF (shipped default), profiles_list == ['default']."""
    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))

    profiles = svc.profiles_list()
    assert set(profiles) == {"default"}, (
        f"clean install must ship only the 'default' profile; got {profiles}"
    )
    assert _DEMO_NAMES.isdisjoint(profiles), (
        f"no demo/test profile residue allowed in shipped defaults; got {profiles}"
    )


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")
def test_demo_profiles_load_when_opted_in(tmp_path, monkeypatch):
    """IR-23: demo/dev/preprod opt-in loads the demo suite from demo-profiles.yaml."""
    monkeypatch.setenv(DEMO_ENABLED, "true")
    import index_tools.tools.service as svc_mod
    svc_mod._RUNTIME_TREE_CACHE = None

    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))

    profiles = set(svc.profiles_list())
    assert "default" in profiles
    assert _DEMO_NAMES.issubset(profiles), (
        f"opted-in demo profiles must be registered; missing "
        f"{_DEMO_NAMES - profiles}; got {sorted(profiles)}"
    )

    ml = svc.profiles.get("multilang", {})
    assert ml.get("enabled") is True
    assert ml.get("backend") == "chroma"
    oc = ml.get("embeddings", {}).get("openai_compat", {})
    assert oc.get("model") == "bge-m3:567m", f"expected bge-m3:567m, got {oc.get('model')}"


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")
def test_default_profile_preserved(tmp_path):
    """Default profile is always present and enabled, demo gating notwithstanding."""
    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))

    assert "default" in svc.profiles_list()
    assert svc.profiles["default"].get("enabled") is True

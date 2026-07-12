"""W28E-1878 (IR-23): demo/test profiles are gated out of the shipped defaults.

Fast, service-init-free coverage of the demo-profiles gate:
 - shipped defaults.yaml carries ZERO demo profiles (residue proof);
 - the gate is OFF by default -> _load_demo_profiles() == {};
 - opting in (CLOUD_DOG__INDEX__DEMO_PROFILES__ENABLED=true) loads the demo suite
   from config/demo-profiles.yaml with ${...} expressions resolved.
"""
from pathlib import Path

import pytest
import yaml

DEMO_ENABLED = "CLOUD_DOG__INDEX__DEMO_PROFILES__ENABLED"

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


def _repo_root() -> Path:
    # tests/unit/<this file> -> <repo>
    return Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    monkeypatch.setenv("CLOUD_DOG__INDEX__VDB__PROVIDER", "chroma")
    monkeypatch.delenv(DEMO_ENABLED, raising=False)
    import index_tools.tools.service as svc_mod
    svc_mod._RUNTIME_TREE_CACHE = None
    yield
    svc_mod._RUNTIME_TREE_CACHE = None


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")
def test_shipped_defaults_yaml_has_no_demo_profiles():
    """The shipped defaults.yaml profiles: section contains ONLY 'default'."""
    data = yaml.safe_load((_repo_root() / "defaults.yaml").read_text(encoding="utf-8"))
    profiles = data.get("profiles", {})
    assert set(profiles.keys()) == {"default"}, (
        f"defaults.yaml must ship only 'default'; got {sorted(profiles.keys())}"
    )
    assert data.get("index", {}).get("demo_profiles", {}).get("enabled") is False


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")
def test_demo_profiles_file_holds_the_suite():
    """config/demo-profiles.yaml holds exactly the moved demo/test profiles."""
    data = yaml.safe_load((_repo_root() / "config" / "demo-profiles.yaml").read_text(encoding="utf-8"))
    assert set(data.get("profiles", {}).keys()) == _DEMO_NAMES


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")
def test_gate_off_by_default():
    """Without opt-in, the demo loader yields nothing."""
    from index_tools.tools.service import _demo_profiles_enabled, _load_demo_profiles
    assert _demo_profiles_enabled() is False
    assert _load_demo_profiles() == {}


@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-002")
def test_gate_on_loads_resolved_suite(monkeypatch):
    """Opt-in loads the full suite with ${...} expressions resolved."""
    monkeypatch.setenv(DEMO_ENABLED, "true")
    import index_tools.tools.service as svc_mod
    svc_mod._RUNTIME_TREE_CACHE = None
    from index_tools.tools.service import _demo_profiles_enabled, _load_demo_profiles

    assert _demo_profiles_enabled() is True
    loaded = _load_demo_profiles()
    assert set(loaded.keys()) == _DEMO_NAMES
    # ${...} expressions are resolved (not literal), e.g. vdb.type -> concrete backend.
    ml = loaded["multilang"]
    assert ml["vdb"]["type"] == "chroma"
    assert "${" not in str(ml["vdb"]["type"])
    assert ml["embeddings"]["openai_compat"]["model"] == "bge-m3:567m"
    nato = loaded["nato-doctrine"]
    assert nato["vdb"]["type"] == "chroma"
    assert "${" not in str(nato["vdb"]["type"])

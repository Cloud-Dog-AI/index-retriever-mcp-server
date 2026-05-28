"""W28D-443: Verify Transparent Borders named profiles load durably from defaults.yaml."""
import os
import pytest


TB_PROFILES = [
    "demo27-transparent-borders",
    "transparent-borders-report-generation-country-reports",
    "transparent-borders-report-generation-knowledge",
    "transparent-borders-report-generation-web-support",
]


@pytest.fixture(autouse=True)
def _set_env():
    os.environ.setdefault("CLOUD_DOG__INDEX__VDB__PROVIDER", "chroma")
    os.environ.setdefault("CLOUD_DOG__INDEX__EMBEDDING__MODEL", "nomic-embed-text")
    os.environ.setdefault("CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY", "test-admin-key")
    os.environ.setdefault("CLOUD_DOG__INDEX__AUTH__API_KEYS", "test-admin-key")


def test_tb_profiles_registered(tmp_path):
    """All four TB profiles must appear in profiles_list after service init."""
    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))

    profiles = svc.profiles_list()
    for name in TB_PROFILES:
        assert name in profiles, f"TB profile '{name}' missing; got {profiles}"
        p = svc.profiles[name]
        assert p.get("enabled") is True, f"{name} not enabled"
        assert p.get("backend") == "chroma", f"{name} backend wrong: {p.get('backend')}"


def test_tb_profiles_have_embeddings_config(tmp_path):
    """Each TB profile must carry its own embeddings config from YAML."""
    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))

    for name in TB_PROFILES:
        p = svc.profiles[name]
        embed = p.get("embeddings", {})
        oc = embed.get("openai_compat", {})
        assert oc.get("model") == "nomic-embed-text", (
            f"{name}: expected nomic-embed-text, got {oc.get('model')}"
        )


def test_tb_profiles_survive_reinit(tmp_path):
    """Simulates restart: create IndexService twice and verify profiles persist."""
    from index_tools.tools.service import IndexService

    svc1 = IndexService(audit_path=str(tmp_path / "audit1.db"))
    profiles1 = svc1.profiles_list()

    svc2 = IndexService(audit_path=str(tmp_path / "audit2.db"))
    profiles2 = svc2.profiles_list()

    for name in TB_PROFILES:
        assert name in profiles1, f"First init missing {name}"
        assert name in profiles2, f"Second init missing {name} (durability fail)"


def test_tb_profiles_coexist_with_defaults(tmp_path):
    """default and multilang must not be affected by TB profile addition."""
    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))

    profiles = svc.profiles_list()
    assert "default" in profiles
    assert "multilang" in profiles

    dp = svc.profiles["default"]
    assert dp.get("enabled") is True

    ml = svc.profiles["multilang"]
    assert ml.get("enabled") is True
    embed = ml.get("embeddings", {})
    oc = embed.get("openai_compat", {})
    assert oc.get("model") == "bge-m3:567m"

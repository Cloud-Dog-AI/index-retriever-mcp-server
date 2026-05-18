"""W28A-295: Verify profiles from YAML config are loaded into IndexService."""
import os
import tempfile
import pytest


@pytest.fixture(autouse=True)
def _set_env():
    os.environ.setdefault("CLOUD_DOG__INDEX__VDB__PROVIDER", "chroma")
    os.environ.setdefault("CLOUD_DOG__INDEX__EMBEDDING__MODEL", "nomic-embed-text")
    os.environ.setdefault("CLOUD_DOG__INDEX__AUTH__ADMIN_API_KEY", "test-admin-key")
    os.environ.setdefault("CLOUD_DOG__INDEX__AUTH__API_KEYS", "test-admin-key")


def test_multilang_profile_registered(tmp_path):
    """defaults.yaml defines a multilang profile; it must appear in profiles_list."""
    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))
    
    profiles = svc.profiles_list()
    assert "default" in profiles, "default profile must exist"
    assert "multilang" in profiles, (
        f"multilang profile from defaults.yaml must be registered; got {profiles}"
    )
    
    ml = svc.profiles.get("multilang", {})
    assert ml.get("enabled") is True
    assert ml.get("backend") == "chroma"
    
    embed = ml.get("embeddings", {})
    oc = embed.get("openai_compat", {})
    assert oc.get("model") == "bge-m3:567m", f"expected bge-m3:567m, got {oc.get('model')}"


def test_default_profile_preserved(tmp_path):
    """Ensure default profile not affected by multilang addition."""
    from index_tools.tools.service import IndexService
    svc = IndexService(audit_path=str(tmp_path / "audit.db"))
    
    profiles = svc.profiles_list()
    assert "default" in profiles
    dp = svc.profiles["default"]
    assert dp.get("enabled") is True

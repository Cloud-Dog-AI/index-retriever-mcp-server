# index-retriever-mcp-server — UT1.4
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests profile config model validation.

from index_tools.config.loader import bind_model
from tests.unit.helpers import minimal_config


def test_profile_model_validation() -> None:
    cfg = bind_model(minimal_config())
    assert "default" in cfg.profiles
    assert cfg.profiles["default"].vdb.type == "chroma"

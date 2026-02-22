# index-retriever-mcp-server — UT1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests invalid config rejection.

import pytest
from pydantic import ValidationError

from index_tools.config.loader import bind_model


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValidationError):
        bind_model({"server": {}})

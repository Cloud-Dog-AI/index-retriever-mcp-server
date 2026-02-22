# index-retriever-mcp-server — QT1.3
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Non-admin users cannot create profiles.

import pytest

from index_tools.tools.service import IndexService


def test_non_admin_cannot_create_profile(service: IndexService) -> None:
    with pytest.raises(PermissionError):
        service.admin_profile_create("restricted", roles={"writer"})

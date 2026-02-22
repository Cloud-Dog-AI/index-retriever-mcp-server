# index-retriever-mcp-server — Admin Endpoints
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Administrative API endpoint handlers.

from __future__ import annotations

from index_tools.tools.service import IndexService


def profile_create(service: IndexService, name: str, roles: set[str]) -> dict[str, str]:
    """Execute profile create."""
    service.admin_profile_create(profile=name, roles=roles)
    return {"status": "created", "profile": name}


def collection_create(service: IndexService, profile: str, collection: str, roles: set[str]) -> dict[str, str]:
    """Execute collection create."""
    service.admin_collection_create(profile=profile, collection=collection, roles=roles)
    return {"status": "created", "collection": collection}

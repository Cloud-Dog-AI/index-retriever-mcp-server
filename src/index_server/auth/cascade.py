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

# W28A-749 — index-retriever resource-aware cascade wiring (consumes cloud_dog_idam 0.5.0 keystone).
"""Capability-gated bridge to the cloud_dog_idam 0.5.0 resource-aware resolver/guard.

The W28A-741 keystone (`cloud_dog_idam.rbac.grants` / `.membership` / `.guard_registry` /
`.secret_masking`) lands in cloud_dog_idam **0.5.0**. This module imports those symbols behind a single
``CASCADE_AVAILABLE`` flag so the service still boots on idam < 0.5.0 (cascade disabled, today's role-based
enforcement preserved). The cascade activates only when the built image carries 0.5.0 — proven at G4
(`pip show cloud-dog-idam == 0.5.0` + the symbol imports below). If 0.5.0 cannot resolve from the normal
internal index, the build fails → PACKAGE_RESOLUTION_BLOCKED (no downgrade / vendor / local-path).

Resource model (W28A-749 WIRING-DESIGN §1):
  - resource_type ``collection``     → resource_id ``"{profile}:{collection}"``  (the CollectionRecord key)
  - resource_type ``index_profile``  → resource_id ``"{profile}"``               (profile-wide grant)
  - resource_id ``"*"``              → every resource of that type in project ``index-retriever``
"""

from __future__ import annotations

from typing import Any, Protocol

#: Project name on every RBACBinding row owned by this service.
PROJECT = "index-retriever"

#: Resource types this service registers with the cloud_dog_idam resource registry.
RESOURCE_TYPE_COLLECTION = "collection"
RESOURCE_TYPE_PROFILE = "index_profile"

# --- 0.5.0 keystone import (capability gate) --------------------------------------
try:
    from cloud_dog_idam.rbac.grants import (  # type: ignore
        allowed_resource_ids as _allowed_resource_ids,
        authorise as _authorise,
        effective_grants as _effective_grants,
    )
    from cloud_dog_idam.rbac.guard_registry import (  # type: ignore
        PUBLIC_ALLOWLIST as _PUBLIC_ALLOWLIST,
        is_route_guarded as _is_route_guarded,
        register_guard as _register_guard,
    )
    from cloud_dog_idam.rbac.resource_registry import (  # type: ignore
        ResourceRegistryService as _ResourceRegistryService,
    )
    from cloud_dog_idam.rbac.secret_masking import mask_secrets as _mask_secrets  # type: ignore
    from cloud_dog_idam.storage.sqlalchemy.models import RBACBindingORM as _RBACBindingORM  # type: ignore
    from cloud_dog_idam.storage.sqlalchemy.repositories import (  # type: ignore
        RBACBindingRepository as _RBACBindingRepository,
    )

    CASCADE_AVAILABLE = True
    authorise = _authorise
    allowed_resource_ids = _allowed_resource_ids
    effective_grants = _effective_grants
    mask_secrets = _mask_secrets
    register_guard = _register_guard
    is_route_guarded = _is_route_guarded
    PUBLIC_ALLOWLIST = _PUBLIC_ALLOWLIST
    ResourceRegistryService = _ResourceRegistryService
    RBACBindingRepository = _RBACBindingRepository
    RBACBindingORM = _RBACBindingORM
except Exception:  # pragma: no cover — idam < 0.5.0 (no resolver/guard); cascade disabled, service still boots
    CASCADE_AVAILABLE = False
    authorise = None  # type: ignore[assignment]
    allowed_resource_ids = None  # type: ignore[assignment]
    effective_grants = None  # type: ignore[assignment]
    register_guard = None  # type: ignore[assignment]
    is_route_guarded = None  # type: ignore[assignment]
    PUBLIC_ALLOWLIST = frozenset()  # type: ignore[assignment]
    ResourceRegistryService = None  # type: ignore[assignment]
    RBACBindingRepository = None  # type: ignore[assignment]
    RBACBindingORM = None  # type: ignore[assignment]

    def mask_secrets(payload: Any, *, is_admin: bool) -> Any:  # type: ignore[misc]
        """Identity fallback when idam < 0.5.0 (no secret_masking surface yet)."""
        return payload


def cascade_symbol_report() -> dict[str, Any]:
    """Return the keystone-symbol presence report used by the G4 in-image proof + T3 gate."""
    return {
        "cascade_available": CASCADE_AVAILABLE,
        "symbols": {
            "grants.effective_grants": effective_grants is not None,
            "grants.allowed_resource_ids": allowed_resource_ids is not None,
            "grants.authorise": authorise is not None,
            "membership": _membership_importable(),
            "guard_registry.register_guard": register_guard is not None,
            "secret_masking.mask_secrets": CASCADE_AVAILABLE,
        },
    }


def _membership_importable() -> bool:
    try:
        import cloud_dog_idam.rbac.membership  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


# --- Membership port (groups_of over the live IndexService group records) ----------
class _ServiceLike(Protocol):
    groups: dict[str, Any]


class IndexMembershipResolver:
    """``cloud_dog_idam.rbac.membership.MembershipResolver`` impl over ``IndexService.groups``.

    The membership edge is the existing ``GroupRecord.members`` join — add/remove-member
    via the existing ``admin_group_*`` path is reflected immediately, which is what makes the
    cascade revoke *live* (no copied-onto-user grant).
    """

    def __init__(self, service: _ServiceLike) -> None:
        self._svc = service

    def groups_of(self, user_id: str) -> set[str]:
        uid = str(user_id or "")
        if not uid:
            return set()
        return {
            gid
            for gid, record in getattr(self._svc, "groups", {}).items()
            if uid in getattr(record, "members", set())
        }


# --- Resource helpers --------------------------------------------------------------
def collection_resource_id(profile: str | None, collection: str | None) -> str:
    """Return the canonical ``collection`` resource_id ``"{profile}:{collection}"``."""
    return f"{str(profile or 'default')}:{str(collection or '')}"


def profile_resource_id(profile: str | None) -> str:
    """Return the canonical ``index_profile`` resource_id ``"{profile}"``."""
    return str(profile or "default")


#: Resource-bearing tools → (permission, resource_type). Tools needing a per-resource
#: authorise() check; resource_id is read from the call args (profile + collection).
#: read = collection.read; write = collection.write (graded). LIST tools use a filter
#: (allowed_resource_ids) instead of a point check — see RESOURCE_LIST_TOOLS.
RESOURCE_POINT_TOOLS: dict[str, tuple[str, str]] = {
    # reads
    "search": ("collection.read", RESOURCE_TYPE_COLLECTION),
    "search_explain": ("collection.read", RESOURCE_TYPE_COLLECTION),
    "retrieve": ("collection.read", RESOURCE_TYPE_COLLECTION),
    "collection_get": ("collection.read", RESOURCE_TYPE_COLLECTION),
    "index_list": ("collection.read", RESOURCE_TYPE_COLLECTION),
    # writes (graded — a read-only binding → 403)
    "ingest_text": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "ingest_upload": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "ingest_reference": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "ingest_preview": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "bulk_index": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "delete_by_id": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "delete_by_filter": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "reindex_run": ("collection.write", RESOURCE_TYPE_COLLECTION),
    "retention_run": ("collection.write", RESOURCE_TYPE_COLLECTION),
}

#: LIST tools whose returned collection set is server-side filtered by allowed_resource_ids.
RESOURCE_LIST_TOOLS: frozenset[str] = frozenset({"collections_list", "list_collections"})


def resource_for_tool(tool_name: str, args: dict[str, Any] | None) -> tuple[str, str, str] | None:
    """Map a resource-bearing tool call to ``(permission, resource_type, resource_id)`` or ``None``.

    Returns None for non-resource-bearing tools (which keep today's resource-agnostic gate).
    """
    spec = RESOURCE_POINT_TOOLS.get(str(tool_name))
    if spec is None:
        return None
    permission, resource_type = spec
    a = args or {}
    rid = collection_resource_id(a.get("profile"), a.get("collection"))
    return (permission, resource_type, rid)

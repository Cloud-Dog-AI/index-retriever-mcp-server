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

"""RBAC enforcement via cloud_dog_idam (PS-70 compliant)."""

from __future__ import annotations

from dataclasses import dataclass

from cloud_dog_idam.rbac import RBACEngine
from cloud_dog_idam.audit.emitter import AuditEmitter
from cloud_dog_idam.audit.models import AuditEvent


@dataclass(slots=True)
class Subject:
    """Subject definition — identity context for RBAC checks."""

    user_id: str
    roles: set[str]


# Module-level audit emitter for IDAM events (PS-70 UM7).
audit_emitter = AuditEmitter(also_log_to_memory=True)


class RbacAuthoriser:
    """RBAC wrapper fully backed by cloud_dog_idam.rbac.RBACEngine."""

    def __init__(self, role_permissions: dict[str, list[str]], default_deny: bool = True) -> None:
        self.role_permissions = {role: set(permissions) for role, permissions in role_permissions.items()}
        self.default_deny = default_deny
        self._engine = RBACEngine(role_permissions=self.role_permissions)

    def is_allowed(self, subject: Subject, permission: str) -> bool:
        """Check if subject has a permission via RBACEngine."""
        for role in subject.roles:
            self._engine.assign_role_to_user(subject.user_id, role)

        allowed = self._engine.has_permission(subject.user_id, permission)
        if not allowed and not self.default_deny:
            allowed = bool(self._engine.get_effective_roles(subject.user_id))
        if not allowed:
            audit_emitter.emit(AuditEvent(
                actor_id=subject.user_id,
                action=permission,
                target="index:rbac",
                outcome="denied",
                details={"roles": sorted(subject.roles)},
            ))
        return allowed

    def backend_name(self) -> str:
        """Return the RBAC backend identifier."""
        return "cloud_dog_idam"

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

from __future__ import annotations

from dataclasses import dataclass

try:
    import cloud_dog_idam  # type: ignore
    from cloud_dog_idam import RBACEngine  # type: ignore
except ImportError:  # pragma: no cover - fallback for local development only
    cloud_dog_idam = None  # type: ignore[assignment]
    RBACEngine = None  # type: ignore[assignment]


@dataclass(slots=True)
class Subject:
    """Subject definition."""

    user_id: str
    roles: set[str]


class RbacAuthoriser:
    """RBAC wrapper backed by cloud_dog_idam role resolution."""

    def __init__(self, role_actions: dict[str, list[str]], default_deny: bool = True) -> None:
        """Initialise the instance state."""
        self.role_actions = {role: set(actions) for role, actions in role_actions.items()}
        self.default_deny = default_deny
        permissions = {role: set(actions) for role, actions in self.role_actions.items()}
        self._engine = RBACEngine(role_permissions=permissions) if RBACEngine is not None else None

    def is_allowed(self, subject: Subject, action: str) -> bool:
        """Execute is allowed."""
        if self._engine is None:
            effective_roles = set(subject.roles)
        else:
            for role in subject.roles:
                self._engine.assign_role_to_user(subject.user_id, role)
            effective_roles = self._engine.get_effective_roles(subject.user_id)

        for role in effective_roles:
            actions = self.role_actions.get(role, set())
            if "*" in actions or action in actions:
                return True
            if action.count("_"):
                prefix = action.split("_", 1)[0] + "_*"
                if prefix in actions:
                    return True
        return not self.default_deny and bool(effective_roles)

    def backend_name(self) -> str:
        """Execute backend name."""
        if cloud_dog_idam is not None and self._engine is not None:
            return "cloud_dog_idam"
        return "fallback"

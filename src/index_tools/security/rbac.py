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

# index-retriever-mcp-server — RBAC Authoriser
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Role-based access checks using cloud_dog_idam semantics.

from __future__ import annotations

from dataclasses import dataclass

try:
    import cloud_dog_idam  # type: ignore
except ImportError:  # pragma: no cover - fallback for local development only
    cloud_dog_idam = None


@dataclass(slots=True)
class Subject:
    """Subject definition."""

    user_id: str
    roles: set[str]


class RbacAuthoriser:
    """Simple RBAC evaluator aligned to cloud_dog_idam role semantics."""

    def __init__(self, role_actions: dict[str, list[str]], default_deny: bool = True) -> None:
        """Initialise the instance state."""
        self.role_actions = {role: set(actions) for role, actions in role_actions.items()}
        self.default_deny = default_deny

    def is_allowed(self, subject: Subject, action: str) -> bool:
        """Execute is allowed."""
        for role in subject.roles:
            actions = self.role_actions.get(role, set())
            if "*" in actions or action in actions:
                return True
            if action.count("_"):
                prefix = action.split("_", 1)[0] + "_*"
                if prefix in actions:
                    return True
        return not self.default_deny and bool(subject.roles)

    def backend_name(self) -> str:
        """Execute backend name."""
        if cloud_dog_idam is not None:
            return "cloud_dog_idam"
        return "fallback"

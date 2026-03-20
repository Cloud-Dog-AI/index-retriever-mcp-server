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

from collections.abc import Callable
from typing import Any


class VdbRegistry:
    """Lookup table for vector backend factory callables."""

    def __init__(self) -> None:
        """Initialise the instance state."""
        self._factories: dict[str, Callable[[], Any]] = {}

    def register(self, backend_type: str, factory: Callable[[], Any]) -> None:
        """Execute register."""
        self._factories[backend_type] = factory

    def get(self, backend_type: str) -> Any:
        """Execute get."""
        # Covers: FR-13
        if backend_type not in self._factories:
            raise KeyError(f"Unsupported vector backend: {backend_type}")
        return self._factories[backend_type]()

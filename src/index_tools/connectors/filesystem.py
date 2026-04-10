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

from cloud_dog_storage import path_utils
from cloud_dog_storage.backends.local import LocalStorage

from index_tools.connectors.models import FetchPlan
from index_tools.security.scope import resolve_scoped_path


def resolve(allowed_roots: list[str], requested_path: str) -> FetchPlan:
    """Execute resolve."""
    path = resolve_scoped_path(allowed_roots=allowed_roots, requested_path=requested_path)
    return FetchPlan(source_type="filesystem", location=str(path), metadata={"scheme": "file"})


def fetch(plan: FetchPlan) -> bytes:
    """Execute fetch via cloud_dog_storage LocalStorage backend."""
    resolved_location = path_utils.resolve_path(plan.location)
    logical_location = path_utils.to_posix(resolved_location)
    storage = LocalStorage(root_path=path_utils.parent(logical_location), min_free_bytes=0)
    return storage.read_bytes(f"/{path_utils.name(logical_location)}")

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

"""ORM models owned by index-retriever-mcp-server."""

from __future__ import annotations

from cloud_dog_db import PlatformBase, TimestampMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class IndexPlatformDbState(PlatformBase, TimestampMixin):
    """Minimal service-owned table proving schema ownership and migrations."""

    __tablename__ = "index_platform_db_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")

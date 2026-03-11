"""ORM models owned by index-retriever-mcp-server."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from cloud_dog_db import PlatformBase, TimestampMixin


class IndexPlatformDbState(PlatformBase, TimestampMixin):
    """Minimal service-owned table proving schema ownership and migrations."""

    __tablename__ = "index_platform_db_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")

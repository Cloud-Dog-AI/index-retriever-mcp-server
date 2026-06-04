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

"""ORM tables for corpus, pattern and template (design brief §10/§11; §25 #8/#9/#10).

Persisted through cloud_dog_db (PlatformBase + TimestampMixin + JSON payload), identical to the
Phase-1 structure tables.
"""

from __future__ import annotations

from typing import Any

from cloud_dog_db import PlatformBase, TimestampMixin
from sqlalchemy import JSON, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class StructureCorpusRow(PlatformBase, TimestampMixin):
    """Named set of structure documents (design brief §10.1)."""

    __tablename__ = "structure_corpora"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    corpus_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    profile_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    collection_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready", index=True)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructurePatternRow(PlatformBase, TimestampMixin):
    """Recurring pattern derived across a corpus (design brief §10.3)."""

    __tablename__ = "structure_patterns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pattern_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    corpus_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    pattern_type: Mapped[str] = mapped_column(String(32), nullable=False, default="section", index=True)
    signature: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    support_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StructureTemplateRow(PlatformBase, TimestampMixin):
    """Generated structure/style blueprint (design brief §11)."""

    __tablename__ = "structure_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    corpus_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["StructureCorpusRow", "StructurePatternRow", "StructureTemplateRow"]

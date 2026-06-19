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

"""Corpus, pattern and template models (design brief §5.2, §10, §11; §25 #8/#9/#10).

Transport-neutral pydantic models for the corpus-analysis and template-intelligence phases,
layered on the Phase-1 canonical structure model.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Derived pattern families (design brief §10.3)."""

    section = "section"
    style = "style"
    layout = "layout"
    table = "table"


class StructureCorpus(BaseModel):
    """A named set of structure documents to analyse together (design brief §5.2, §10.1)."""

    corpus_id: str = ""
    name: str
    profile_id: str
    collection_id: str | None = None
    description: str | None = None
    document_ids: list[str] = Field(default_factory=list)
    document_count: int = 0
    status: str = "ready"
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructurePattern(BaseModel):
    """A recurring pattern derived across a corpus (design brief §5.2, §10.2/§10.3)."""

    pattern_id: str = ""
    corpus_id: str = ""
    pattern_type: PatternType = PatternType.section
    signature: str = ""
    label: str | None = None
    support_count: int = 0
    document_count: int = 0
    confidence: float = 0.0
    examples: list[Any] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CorpusReport(BaseModel):
    """Aggregate corpus analysis output (design brief §10.2)."""

    corpus_id: str = ""
    document_count: int = 0
    pattern_count: int = 0
    section_type_distribution: dict[str, int] = Field(default_factory=dict)
    style_class_distribution: dict[str, int] = Field(default_factory=dict)
    block_type_distribution: dict[str, int] = Field(default_factory=dict)
    dominant_section_sequence: list[str] = Field(default_factory=list)
    patterns: list[StructurePattern] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateSection(BaseModel):
    """One section in a generated template blueprint (design brief §11.1/§11.2)."""

    order: int = 0
    section_type: str = "unknown"
    title: str | None = None
    level: int = 0
    block_type_signature: list[str] = Field(default_factory=list)
    style_hint: str | None = None
    support_count: int = 0
    confidence: float = 0.0
    source_document_ids: list[str] = Field(default_factory=list)
    variation_titles: list[str] = Field(default_factory=list)


class StructureTemplate(BaseModel):
    """A reusable structure/style blueprint generated from corpus patterns (design brief §11)."""

    template_id: str = ""
    corpus_id: str = ""
    name: str = ""
    profile_id: str = ""
    sections: list[TemplateSection] = Field(default_factory=list)
    style_guide: dict[str, Any] = Field(default_factory=dict)
    source_pattern_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateExport(BaseModel):
    """Rendered export of a template (design brief §11.3)."""

    template_id: str = ""
    format: str = "markdown"
    content: str = ""

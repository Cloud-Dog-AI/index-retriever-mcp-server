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

"""Template intelligence: blueprint generation + export (design brief §11; §25 #10)."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from index_tools.structure.corpus_models import (
    PatternType,
    StructureTemplate,
    TemplateExport,
    TemplateSection,
)
from index_tools.structure.corpus_repository import CorpusRepository


class TemplateService:
    """Generate, store, and export structure/style templates from corpus patterns (transport-neutral)."""

    def __init__(self, *, repository: CorpusRepository | None = None, audit_logger: Any | None = None) -> None:
        """Bind the corpus repository (corpus + patterns + templates) and optional audit logger."""
        self.repository = repository or CorpusRepository()
        self.audit_logger = audit_logger

    def _audit(self, *, actor: str, roles: set[str] | None, action: str, target_id: str, **details: Any) -> None:
        logger = self.audit_logger
        log = getattr(logger, "log_admin_action", None) if logger is not None else None
        if callable(log):
            log(actor=actor, roles=set(roles or set()), action=action, target_type="structure_template", target_id=target_id, target_name=target_id, **details)

    def generate(self, corpus_id: str, *, name: str | None = None, actor: str = "service", roles: set[str] | None = None) -> dict[str, Any]:
        """Assemble a template blueprint from a corpus's analysed patterns (design brief §11.1)."""
        corpus = self.repository.get_corpus(corpus_id)
        if corpus is None:
            raise KeyError(corpus_id)
        section_patterns = self.repository.list_patterns(corpus_id, pattern_type=PatternType.section.value)
        style_patterns = self.repository.list_patterns(corpus_id, pattern_type=PatternType.style.value)
        table_patterns = self.repository.list_patterns(corpus_id, pattern_type=PatternType.table.value)
        if not section_patterns:
            raise ValueError(f"corpus {corpus_id} has no analysed section patterns; run analyse first")

        top = section_patterns[0]
        sequence = list(top.detail.get("sequence", [])) or top.signature.split("->")
        sequence_details = list(top.detail.get("sequence_details", []))
        source_document_ids = list(top.detail.get("source_document_ids", []))
        title_variations = dict(top.detail.get("title_variations", {}))
        sections: list[TemplateSection] = []
        for order, section_type in enumerate(sequence):
            detail = sequence_details[order] if order < len(sequence_details) and isinstance(sequence_details[order], dict) else {}
            observed_title = str(detail.get("title") or detail.get("normalised_title") or "").strip()
            variation_map = title_variations.get(str(order), {})
            variations = list(variation_map.keys()) if isinstance(variation_map, dict) else []
            title = observed_title or section_type.replace("_", " ").title()
            generated_type = section_type
            if section_type == "unknown" and observed_title:
                generated_type = _normalise_section_key(observed_title)
            sections.append(
                TemplateSection(
                    order=order,
                    section_type=generated_type,
                    title=title,
                    level=int(detail.get("level", 0 if order == 0 else 1) or 0),
                    block_type_signature=["heading", "paragraph"],
                    style_hint=f"heading_{0 if order == 0 else 1}",
                    support_count=top.support_count,
                    confidence=top.confidence,
                    source_document_ids=source_document_ids,
                    variation_titles=variations,
                )
            )

        style_guide = {
            "dominant_styles": [
                {"style_class": p.detail.get("style_class", p.signature), "support": p.support_count, "confidence": p.confidence}
                for p in style_patterns[:8]
            ],
            "table_shapes": [{"shape": p.signature, "support": p.support_count} for p in table_patterns[:5]],
        }

        template = StructureTemplate(
            template_id=f"tmpl_{uuid4().hex}",
            corpus_id=corpus_id,
            name=name or f"{corpus.name} template",
            profile_id=corpus.profile_id,
            sections=sections,
            style_guide=style_guide,
            source_pattern_ids=[p.pattern_id for p in section_patterns[:1]] + [p.pattern_id for p in style_patterns[:8]],
            confidence=top.confidence,
            created_by=actor,
            metadata={
                "source_document_ids": source_document_ids,
                "section_title_variations": title_variations,
            },
        )
        stored = self.repository.upsert_template(template)
        self._audit(actor=actor, roles=roles, action="generate", target_id=stored.template_id, new_value={"corpus_id": corpus_id, "sections": len(sections)})
        return stored.model_dump(mode="json")

    def get(self, template_id: str) -> dict[str, Any]:
        template = self.repository.get_template(template_id)
        if template is None:
            raise KeyError(template_id)
        return template.model_dump(mode="json")

    def list(self, *, profile_id: str | None = None, corpus_id: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        templates, total = self.repository.list_templates(profile_id=profile_id, corpus_id=corpus_id, limit=limit, offset=offset)
        return {"templates": [t.model_dump(mode="json") for t in templates], "total": total, "limit": limit, "offset": offset}

    def export(self, template_id: str, *, format: str = "markdown") -> dict[str, Any]:
        """Render a template as Markdown or JSON (design brief §11.3)."""
        template = self.repository.get_template(template_id)
        if template is None:
            raise KeyError(template_id)
        fmt = (format or "markdown").strip().lower()
        if fmt == "json":
            content = json.dumps(template.model_dump(mode="json"), indent=2, sort_keys=True)
        elif fmt in {"markdown", "md"}:
            content = _render_markdown(template)
            fmt = "markdown"
        else:
            raise ValueError(f"unsupported export format: {format}")
        return TemplateExport(template_id=template_id, format=fmt, content=content).model_dump(mode="json")

    def delete(self, template_id: str, *, actor: str = "service", roles: set[str] | None = None) -> dict[str, Any]:
        """Delete a generated template through the supported lifecycle path."""
        existing = self.repository.get_template(template_id)
        if existing is None:
            raise KeyError(template_id)
        deleted = self.repository.delete_template(template_id)
        self._audit(
            actor=actor,
            roles=roles,
            action="delete",
            target_id=template_id,
            old_value={"corpus_id": existing.corpus_id, "name": existing.name},
        )
        return {"template_id": template_id, "deleted": bool(deleted), "corpus_id": existing.corpus_id}


def _normalise_section_key(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")
    return value or "unknown"


def _render_markdown(template: StructureTemplate) -> str:
    lines = [f"# {template.name}", "", f"_Generated from corpus `{template.corpus_id}` (confidence {template.confidence})._", "", "## Section blueprint", ""]
    for section in template.sections:
        prefix = "#" * (section.level + 2)
        lines.append(f"{prefix} {section.title}  ({section.section_type})")
        lines.append(f"- blocks: {', '.join(section.block_type_signature)}")
        if section.style_hint:
            lines.append(f"- style: {section.style_hint}")
        if section.support_count:
            lines.append(f"- support: {section.support_count}, confidence: {section.confidence}")
        if section.source_document_ids:
            lines.append(f"- sources: {', '.join(section.source_document_ids)}")
        if section.variation_titles:
            lines.append(f"- title variants: {', '.join(section.variation_titles)}")
        lines.append("")
    dominant = template.style_guide.get("dominant_styles", [])
    if dominant:
        lines.append("## Style guide")
        lines.append("")
        for entry in dominant:
            lines.append(f"- `{entry.get('style_class')}` — support {entry.get('support')}, confidence {entry.get('confidence')}")
        lines.append("")
    return "\n".join(lines)

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
        sections: list[TemplateSection] = []
        for order, section_type in enumerate(sequence):
            sections.append(
                TemplateSection(
                    order=order,
                    section_type=section_type,
                    title=section_type.replace("_", " ").title(),
                    level=0 if order == 0 else 1,
                    block_type_signature=["heading", "paragraph"],
                    style_hint=f"heading_{0 if order == 0 else 1}",
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


def _render_markdown(template: StructureTemplate) -> str:
    lines = [f"# {template.name}", "", f"_Generated from corpus `{template.corpus_id}` (confidence {template.confidence})._", "", "## Section blueprint", ""]
    for section in template.sections:
        prefix = "#" * (section.level + 2)
        lines.append(f"{prefix} {section.title}  ({section.section_type})")
        lines.append(f"- blocks: {', '.join(section.block_type_signature)}")
        if section.style_hint:
            lines.append(f"- style: {section.style_hint}")
        lines.append("")
    dominant = template.style_guide.get("dominant_styles", [])
    if dominant:
        lines.append("## Style guide")
        lines.append("")
        for entry in dominant:
            lines.append(f"- `{entry.get('style_class')}` — support {entry.get('support')}, confidence {entry.get('confidence')}")
        lines.append("")
    return "\n".join(lines)

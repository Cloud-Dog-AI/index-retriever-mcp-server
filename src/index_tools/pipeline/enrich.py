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

"""Ingest-time outbound enrichment pipeline step."""

from __future__ import annotations

import ast
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class EnricherClient(Protocol):
    """Protocol shared by outbound MCP and A2A clients."""

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Invoke an enrichment tool or skill."""


@dataclass(frozen=True, slots=True)
class EnrichStepConfig:
    """Parsed enrich step configuration."""

    service: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    transport: str = "mcp"
    required: bool = False
    merge_key: str = ""

    @property
    def enrichment_key(self) -> str:
        """Return the metadata key used to store this enrichment result."""
        return self.merge_key or f"{self.service}.{self.tool}"


async def apply_enrich_step(
    document: dict[str, Any],
    step: EnrichStepConfig,
    client: EnricherClient,
    *,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Invoke one enricher and merge its normalized result into a document."""
    if not step.enabled:
        return document
    arguments = resolve_arguments(step.arguments, document)
    result = await client.invoke_tool(step.tool, arguments, correlation_id=correlation_id)
    return merge_enrichment_result(document, step, result)


async def apply_enrich_steps(
    document: dict[str, Any],
    steps: list[EnrichStepConfig],
    client_factory: Callable[[EnrichStepConfig], EnricherClient | Awaitable[EnricherClient]],
    *,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Apply each enabled enrich step, optionally recording non-required failures."""
    current = document
    for step in steps:
        if not step.enabled:
            continue
        try:
            client = client_factory(step)
            if hasattr(client, "__await__"):
                client = await client  # type: ignore[assignment]
            current = await apply_enrich_step(current, step, client, correlation_id=correlation_id)  # type: ignore[arg-type]
        except Exception as exc:
            if step.required:
                raise
            metadata = _metadata(current)
            errors = metadata.setdefault("enrichment_errors", [])
            if isinstance(errors, list):
                errors.append({"step": step.enrichment_key, "error": str(exc)[:500]})
    return current


def enrich_steps_from_metadata(*metadata_blocks: Mapping[str, Any] | None) -> list[EnrichStepConfig]:
    """Build enrich steps from source-config or ingest metadata blocks."""
    steps: list[EnrichStepConfig] = []
    for metadata in metadata_blocks:
        if not isinstance(metadata, Mapping):
            continue
        steps.extend(_steps_from_block(metadata.get("pipeline")))
        steps.extend(_steps_from_block(metadata.get("enrichers")))
        enrich_block = metadata.get("enrich")
        if isinstance(enrich_block, Mapping):
            if enrich_block.get("enabled", True) is False:
                continue
            steps.extend(_steps_from_block(enrich_block.get("steps")))
            if "step" in enrich_block:
                steps.extend(_steps_from_block(enrich_block.get("step")))
        elif isinstance(enrich_block, (str, list, tuple)):
            steps.extend(_steps_from_block(enrich_block))
    return steps


def parse_enrich_spec(spec: str) -> EnrichStepConfig:
    """Parse syntax like ``search-mcp.enrich(query=$doc.title, depth=quick)``."""
    raw = str(spec or "").strip()
    if not raw:
        raise ValueError("enrich step must not be empty")
    call = raw
    arg_text = ""
    if "(" in raw and raw.endswith(")"):
        call, arg_text = raw[:-1].split("(", 1)
    if "." not in call:
        raise ValueError(f"enrich step must name service.tool: {raw}")
    service, tool = call.split(".", 1)
    arguments = _parse_arguments(arg_text)
    return EnrichStepConfig(service=service.strip(), tool=tool.strip(), arguments=arguments)


def resolve_arguments(arguments: Mapping[str, Any], document: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve ``$doc.<path>`` argument references against the ingest document."""
    return {str(key): _resolve_value(value, document) for key, value in arguments.items()}


def merge_enrichment_result(
    document: dict[str, Any],
    step: EnrichStepConfig,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge an enrichment response into document metadata."""
    output = dict(document)
    metadata = _metadata(output)
    payload = normalise_enrichment_payload(result)
    enrichment_map = metadata.setdefault("enrichment", {})
    if isinstance(enrichment_map, dict):
        enrichment_map[step.enrichment_key] = payload
    metadata["enrichment_status"] = "enriched"

    for key in ("related_content", "quality_classifications", "quality", "entities"):
        if key in payload:
            metadata[key] = payload[key]
            output[key] = payload[key]
    if "metadata" in payload and isinstance(payload["metadata"], dict):
        metadata.update(payload["metadata"])
    output["metadata"] = metadata
    return output


def normalise_enrichment_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize MCP/A2A result envelopes into a mergeable mapping."""
    for key in ("result", "data", "output"):
        nested = result.get(key)
        if isinstance(nested, dict):
            return dict(nested)
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
    return dict(result)


def _steps_from_block(value: Any) -> list[EnrichStepConfig]:
    if value is None:
        return []
    if isinstance(value, str):
        return [parse_enrich_spec(value)]
    if isinstance(value, Mapping):
        if "enrich" in value:
            step = parse_enrich_spec(str(value["enrich"]))
            return [_with_overrides(step, value)]
        if "service" in value and "tool" in value:
            arguments = value.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}
            return [
                EnrichStepConfig(
                    service=str(value["service"]),
                    tool=str(value["tool"]),
                    arguments=dict(arguments),
                    enabled=bool(value.get("enabled", True)),
                    transport=str(value.get("transport", "mcp") or "mcp"),
                    required=bool(value.get("required", False)),
                    merge_key=str(value.get("merge_key", "") or ""),
                )
            ]
        return []
    if isinstance(value, (list, tuple)):
        steps: list[EnrichStepConfig] = []
        for item in value:
            steps.extend(_steps_from_block(item))
        return steps
    return []


def _with_overrides(step: EnrichStepConfig, value: Mapping[str, Any]) -> EnrichStepConfig:
    return EnrichStepConfig(
        service=step.service,
        tool=step.tool,
        arguments=step.arguments,
        enabled=bool(value.get("enabled", step.enabled)),
        transport=str(value.get("transport", step.transport) or step.transport),
        required=bool(value.get("required", step.required)),
        merge_key=str(value.get("merge_key", step.merge_key) or step.merge_key),
    )


def _parse_arguments(arg_text: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for part in _split_args(arg_text):
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"invalid enrich argument: {part}")
        key, value = part.split("=", 1)
        output[key.strip()] = _parse_literal(value.strip())
    return output


def _split_args(arg_text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote = ""
    depth = 0
    for char in arg_text:
        if quote:
            current.append(char)
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}" and depth:
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current).strip())
    return parts


def _parse_literal(raw: str) -> Any:
    if raw.startswith("$doc."):
        return raw
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"none", "null"}:
        return None
    try:
        return ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return raw


def _resolve_value(value: Any, document: Mapping[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$doc."):
        return _resolve_doc_path(document, value[len("$doc.") :])
    if isinstance(value, dict):
        return {key: _resolve_value(nested, document) for key, nested in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, document) for item in value]
    return value


def _resolve_doc_path(document: Mapping[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
            continue
        metadata = current.get("metadata") if isinstance(current, Mapping) else None
        if isinstance(metadata, Mapping) and part in metadata:
            current = metadata[part]
            continue
        return None
    return current


def _metadata(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    metadata = {}
    document["metadata"] = metadata
    return metadata

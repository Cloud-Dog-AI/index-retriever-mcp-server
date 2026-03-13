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

# index-retriever-mcp-server — IT2 Matrix Helpers
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared helpers for W23A IT2 backend/parser matrix tests.

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tests.w23a_helpers import corpus_file, parser_registry_from_services


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return max(default, minimum)
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(value, minimum)


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _mineru_base_candidates(base_url: str) -> list[str]:
    out = [base_url.rstrip("/")]
    if "mineruapi" in base_url:
        candidate = base_url.replace("mineruapi", "minerugui").rstrip("/")
        if candidate not in out:
            out.append(candidate)
    return out


def _parse_gradio_upload_path(payload: Any) -> str:
    if isinstance(payload, list) and payload:
        first = payload[0]
        return first if isinstance(first, str) else ""
    if isinstance(payload, dict):
        candidate = payload.get("path")
        return candidate if isinstance(candidate, str) else ""
    return ""


def _parse_gradio_markdown(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    if not isinstance(data, list):
        return ""
    if len(data) > 1 and isinstance(data[1], str) and data[1].strip():
        return data[1]
    if data and isinstance(data[0], str) and data[0].strip():
        return data[0]
    return ""


def _looks_like_table_text(text: str) -> bool:
    lowered = text.lower()
    if "<table" in lowered and "<tr" in lowered:
        return True
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    for line in lines[:500]:
        if line.count("|") >= 2:
            return True
        if re.search(r"\S+\s{2,}\S+\s{2,}\S+", line):
            return True
        if len(re.findall(r"\d[\d,]*(?:\.\d+)?", line)) >= 3 and len(line.split()) >= 4:
            return True
    return False


def _parse_mineru_via_requests_sync(
    *,
    base_url: str,
    api_key: str,
    document: bytes,
    filename: str,
    mime_type: str | None,
    parse_options: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        import requests
    except Exception as exc:  # pragma: no cover - environment guard
        raise RuntimeError(f"requests transport unavailable: {exc}") from exc

    timeout = max(float(timeout_seconds or 0.0), 60.0)
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    errors: list[str] = []
    files = {"files": (filename, document, mime_type or "application/octet-stream")}
    for candidate_base in _mineru_base_candidates(base_url):
        upload_url = f"{candidate_base}/gradio_api/upload"
        try:
            upload_resp = requests.post(upload_url, headers=headers, files=files, timeout=(10.0, timeout))
        except Exception as exc:
            errors.append(f"{candidate_base}:upload:{type(exc).__name__}:{exc}")
            continue
        if upload_resp.status_code >= 400:
            errors.append(f"{candidate_base}:upload:{upload_resp.status_code}:{upload_resp.text[:200]}")
            continue

        try:
            upload_payload = upload_resp.json()
        except json.JSONDecodeError as exc:
            errors.append(f"{candidate_base}:upload:non_json:{exc}")
            continue
        remote_path = _parse_gradio_upload_path(upload_payload)
        if not remote_path:
            errors.append(f"{candidate_base}:upload:missing_path")
            continue

        end_pages = 1000
        if "end_page_id" in parse_options:
            try:
                end_pages = max(int(parse_options.get("end_page_id", 0)) + 1, 1)
            except (TypeError, ValueError):
                end_pages = 1000
        run_payload = {
            "data": [
                {"path": remote_path, "meta": {"_type": "gradio.FileData"}},
                end_pages,
                str(parse_options.get("parse_method", "")).strip().lower() == "ocr",
                _coerce_bool(parse_options.get("formula_enable"), True),
                _coerce_bool(parse_options.get("table_enable"), True),
                str(parse_options.get("lang_list", "en (English)")) or "en (English)",
                str(parse_options.get("parse_backend", parse_options.get("backend", "pipeline"))) or "pipeline",
                str(parse_options.get("server_url", "http://localhost:30000")) or "http://localhost:30000",
            ]
        }
        run_url = f"{candidate_base}/gradio_api/run/to_markdown"
        try:
            run_resp = requests.post(run_url, headers=headers, json=run_payload, timeout=(10.0, timeout))
        except Exception as exc:
            errors.append(f"{candidate_base}:run:{type(exc).__name__}:{exc}")
            continue
        if run_resp.status_code >= 400:
            errors.append(f"{candidate_base}:run:{run_resp.status_code}:{run_resp.text[:200]}")
            continue

        try:
            run_payload_json = run_resp.json()
        except json.JSONDecodeError as exc:
            errors.append(f"{candidate_base}:run:non_json:{exc}")
            continue
        markdown = _parse_gradio_markdown(run_payload_json).strip()
        if markdown:
            return {
                "text": markdown,
                "metadata": {"transport": "requests_fallback", "endpoint": candidate_base},
                "provider_version": "api-0.1.0+requests-fallback",
            }
        errors.append(f"{candidate_base}:run:empty_markdown")

    detail = " | ".join(errors[:6]) if errors else "no candidate endpoint succeeded"
    try:
        return _parse_mineru_via_curl_sync(
            base_url=base_url,
            document=document,
            filename=filename,
            mime_type=mime_type,
            parse_options=parse_options,
            timeout_seconds=timeout_seconds,
        )
    except Exception as curl_exc:
        raise RuntimeError(f"mineru requests fallback failed: {detail}; curl fallback failed: {curl_exc}") from curl_exc


def _curl_post_capture(*, args: list[str], timeout_seconds: float) -> tuple[int, str]:
    wrapped = args + ["-w", "\n__HTTP__:%{http_code}"]
    proc = subprocess.run(
        wrapped,
        check=False,
        capture_output=True,
        text=True,
        timeout=max(int(timeout_seconds) + 15, 30),
    )
    output = str(proc.stdout or "")
    if "\n__HTTP__:" not in output:
        stderr = str(proc.stderr or "").strip()
        raise RuntimeError(f"curl output parse failed (rc={proc.returncode}): {stderr}")
    body, raw_code = output.rsplit("\n__HTTP__:", 1)
    try:
        code = int(raw_code.strip().splitlines()[0])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"curl http code parse failed: {raw_code!r}") from exc
    return code, body


def _parse_mineru_via_curl_sync(
    *,
    base_url: str,
    document: bytes,
    filename: str,
    mime_type: str | None,
    parse_options: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    timeout = max(float(timeout_seconds or 0.0), 60.0)
    errors: list[str] = []
    with tempfile.NamedTemporaryFile(prefix="mineru-", suffix=Path(filename).suffix or ".pdf", delete=True) as tmp:
        tmp.write(document)
        tmp.flush()
        for candidate_base in _mineru_base_candidates(base_url):
            upload_args = [
                "curl",
                "-sS",
                "--max-time",
                str(int(timeout)),
                "-X",
                "POST",
                "-F",
                f"files=@{tmp.name};type={mime_type or 'application/octet-stream'}",
                f"{candidate_base}/gradio_api/upload",
            ]
            try:
                upload_code, upload_body = _curl_post_capture(args=upload_args, timeout_seconds=timeout)
            except Exception as exc:
                errors.append(f"{candidate_base}:upload:{type(exc).__name__}:{exc}")
                continue
            if upload_code >= 400:
                errors.append(f"{candidate_base}:upload:{upload_code}:{upload_body[:200]}")
                continue
            try:
                upload_payload = json.loads(upload_body)
            except json.JSONDecodeError as exc:
                errors.append(f"{candidate_base}:upload:non_json:{exc}")
                continue
            remote_path = _parse_gradio_upload_path(upload_payload)
            if not remote_path:
                errors.append(f"{candidate_base}:upload:missing_path")
                continue

            end_pages = 1000
            if "end_page_id" in parse_options:
                try:
                    end_pages = max(int(parse_options.get("end_page_id", 0)) + 1, 1)
                except (TypeError, ValueError):
                    end_pages = 1000
            run_payload = {
                "data": [
                    {"path": remote_path, "meta": {"_type": "gradio.FileData"}},
                    end_pages,
                    str(parse_options.get("parse_method", "")).strip().lower() == "ocr",
                    _coerce_bool(parse_options.get("formula_enable"), True),
                    _coerce_bool(parse_options.get("table_enable"), True),
                    str(parse_options.get("lang_list", "en (English)")) or "en (English)",
                    str(parse_options.get("parse_backend", parse_options.get("backend", "pipeline"))) or "pipeline",
                    str(parse_options.get("server_url", "http://localhost:30000")) or "http://localhost:30000",
                ]
            }
            run_args = [
                "curl",
                "-sS",
                "--max-time",
                str(int(timeout)),
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(run_payload),
                f"{candidate_base}/gradio_api/run/to_markdown",
            ]
            try:
                run_code, run_body = _curl_post_capture(args=run_args, timeout_seconds=timeout)
            except Exception as exc:
                errors.append(f"{candidate_base}:run:{type(exc).__name__}:{exc}")
                continue
            if run_code >= 400:
                errors.append(f"{candidate_base}:run:{run_code}:{run_body[:200]}")
                continue
            try:
                run_payload_json = json.loads(run_body)
            except json.JSONDecodeError as exc:
                errors.append(f"{candidate_base}:run:non_json:{exc}")
                continue
            markdown = _parse_gradio_markdown(run_payload_json).strip()
            if markdown:
                return {
                    "text": markdown,
                    "metadata": {"transport": "curl-fallback", "endpoint": candidate_base},
                    "provider_version": "api-0.1.0+curl-fallback",
                }
            errors.append(f"{candidate_base}:run:empty_markdown")

    detail = " | ".join(errors[:6]) if errors else "no candidate endpoint succeeded"
    raise RuntimeError(detail)


async def parse_pdf_with_provider(
    provider_id: str,
    *,
    source_path: Path | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = parser_registry_from_services()
    provider = registry.get(provider_id)
    if provider is None:
        raise RuntimeError(f"parser provider not registered: {provider_id}")

    pdf = source_path or corpus_file("Examples.pdf")
    document = pdf.read_bytes()
    parse_options = dict(options or {})
    if provider_id.strip().lower() == "mineru":
        # Mirror platform-vdb low-VRAM defaults to avoid long-running parser stalls.
        parse_options.setdefault("parse_backend", str(os.getenv("MINERU_PARSE_BACKEND", "pipeline") or "pipeline"))
        parse_options.setdefault("parse_method", str(os.getenv("MINERU_PARSE_METHOD", "auto") or "auto"))
        parse_options.setdefault("formula_enable", _env_bool("MINERU_FORMULA_ENABLE", False))
        parse_options.setdefault("table_enable", _env_bool("MINERU_TABLE_ENABLE", False))
        parse_options.setdefault("return_middle_json", _env_bool("MINERU_RETURN_MIDDLE_JSON", False))
        parse_options.setdefault("return_images", _env_bool("MINERU_RETURN_IMAGES", False))
        parse_options.setdefault("start_page_id", _env_int("MINERU_START_PAGE_ID", 0, minimum=0))
        parse_options.setdefault("end_page_id", _env_int("MINERU_END_PAGE_ID", 0, minimum=0))
        parse_options.setdefault("page_fallback_enabled", True)
        parse_options.setdefault("page_fallback_max_pages", _env_int("MINERU_PAGE_FALLBACK_MAX_PAGES", 24, minimum=1))
        parse_options.setdefault("page_fallback_target_chars", _env_int("MINERU_PAGE_FALLBACK_TARGET_CHARS", 3200, minimum=0))
    if provider_id.strip().lower() == "marker_mcp":
        # Keep marker MCP integration calls bounded on shared test workers.
        parse_options.setdefault("page_range", 0)
        parse_options.setdefault("async_mode", False)

    source_uri = f"file://{pdf.name}"

    if provider_id.strip().lower() == "mineru":
        attempts = _env_int("MINERU_PARSE_ATTEMPTS", 3, minimum=1)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                ir = await provider.parse_bytes(
                    document,
                    filename=pdf.name,
                    source_uri=source_uri,
                    mime_type="application/pdf",
                    options=parse_options,
                )
                break
            except Exception as exc:
                last_error = exc
                message = f"{type(exc).__name__}: {exc}".lower()
                transient = "readerror" in message or "connecttimeout" in message or "timed out" in message
                if transient and attempt + 1 < attempts:
                    await asyncio.sleep(min(5.0, float(attempt + 1)))
                    continue
                if transient:
                    fallback = await asyncio.to_thread(
                        _parse_mineru_via_requests_sync,
                        base_url=str(getattr(provider, "base_url", "")),
                        api_key=str(getattr(provider, "api_key", "")),
                        document=document,
                        filename=pdf.name,
                        mime_type="application/pdf",
                        parse_options=parse_options,
                        timeout_seconds=float(os.getenv("MINERU_DOC_TIMEOUT_SECONDS", "240") or 240),
                    )
                    full_text = str(fallback.get("text", "")).strip()
                    if full_text:
                        has_markdown_table = _looks_like_table_text(full_text)
                        metadata = dict(fallback.get("metadata", {}))
                        return {
                            "provider_id": "mineru",
                            "provider_version": str(fallback.get("provider_version", "api-0.1.0")),
                            "source_uri": source_uri,
                            "text_chars": len(full_text),
                            "text_blocks": max(1, len([line for line in full_text.splitlines() if line.strip()])),
                            "table_blocks": 0,
                            "has_markdown_table": has_markdown_table,
                            "metadata": metadata,
                            "quality": {"confidence": 0.86},
                        }
                raise
        else:  # pragma: no cover - defensive branch
            if last_error is not None:
                raise last_error
            raise RuntimeError("mineru parse failed without error context")
    else:
        ir = await provider.parse_bytes(
            document,
            filename=pdf.name,
            source_uri=source_uri,
            mime_type="application/pdf",
            options=parse_options,
        )
    full_text = ir.full_text()
    has_markdown_table = _looks_like_table_text(full_text)
    return {
        "provider_id": str(ir.provider_id),
        "provider_version": str(ir.provider_version),
        "source_uri": str(ir.source_uri),
        "text_chars": len(full_text),
        "text_blocks": len(ir.text_blocks),
        "table_blocks": len(ir.table_blocks),
        "has_markdown_table": has_markdown_table,
        "metadata": dict(ir.metadata),
        "quality": dict(ir.quality),
    }


def available_parser_ids() -> list[str]:
    registry = parser_registry_from_services()
    return registry.list_ids()

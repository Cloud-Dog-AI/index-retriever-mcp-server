"""W28A-70 static checks for requirements/tests/code traceability."""

from __future__ import annotations

import json
import re
from pathlib import Path


def _ordered_requirement_ids(text: str, pattern: re.Pattern[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        req_id = match.group(0)
        if req_id in seen:
            continue
        seen.add(req_id)
        ordered.append(req_id)
    return ordered


def _test_id_from_path(path: Path) -> str | None:
    rel = path.as_posix()
    match = re.search(r"/(UT|ST|IT|AT|QT|CT|PT)(\d+)_(\d+)", rel)
    if not match:
        return None
    return f"{match.group(1)}{match.group(2)}.{match.group(3)}"


def _status(has_code: bool, has_test: bool) -> str:
    if has_code and has_test:
        return "DELIVERED"
    if has_code and not has_test:
        return "UNTESTED"
    if (not has_code) and has_test:
        return "PARTIAL"
    return "NOT_STARTED"


def test_traceability_source_docs_exist(requirements_doc: Path, tests_doc: Path) -> None:
    """Traceability inputs must exist."""
    assert requirements_doc.exists(), "Missing REQUIREMENTS.md"
    assert tests_doc.exists(), "Missing TESTS.md"


def test_delivery_matrix_generated_for_all_requirements(
    project_root: Path,
    requirements_doc: Path,
    tests_doc: Path,
    requirement_id_pattern: re.Pattern[str],
    src_text: str,
    tests_text: str,
) -> None:
    """Generate full Req -> Code -> Test delivery matrix for audit reporting."""
    requirements_text = requirements_doc.read_text(encoding="utf-8")
    tests_doc_text = tests_doc.read_text(encoding="utf-8")
    req_ids = _ordered_requirement_ids(requirements_text, requirement_id_pattern)

    rows: list[dict[str, object]] = []
    for req_id in req_ids:
        has_code = req_id in src_text
        has_test = req_id in tests_doc_text or req_id in tests_text
        rows.append(
            {
                "requirement_id": req_id,
                "has_code": has_code,
                "has_test": has_test,
                "status": _status(has_code, has_test),
            }
        )

    matrix_md = [
        "# W25A Delivery Matrix (Auto-Generated)",
        "",
        "| Requirement | Code | Test | Status |",
        "|---|---|---|---|",
    ]
    for row in rows:
        matrix_md.append(
            f"| {row['requirement_id']} | {'Y' if row['has_code'] else 'N'} | "
            f"{'Y' if row['has_test'] else 'N'} | {row['status']} |"
        )

    output = project_root / "working" / "W25A-traceability-matrix.md"
    output.write_text("\n".join(matrix_md) + "\n", encoding="utf-8")

    assert req_ids, "No requirement IDs detected in REQUIREMENTS.md"
    assert len(rows) == len(req_ids), "Traceability matrix row count mismatch"
    assert output.exists(), "Traceability matrix artifact was not written"


def test_traceability_gap_report_generated(
    project_root: Path,
    requirements_doc: Path,
    tests_doc: Path,
    requirement_id_pattern: re.Pattern[str],
    src_text: str,
    tests_text: str,
    test_python_files: list[Path],
) -> None:
    """Generate gap report for untested/unimplemented requirements and orphan tests."""
    requirements_text = requirements_doc.read_text(encoding="utf-8")
    tests_doc_text = tests_doc.read_text(encoding="utf-8")
    req_ids = _ordered_requirement_ids(requirements_text, requirement_id_pattern)

    untested = [req_id for req_id in req_ids if req_id not in tests_doc_text and req_id not in tests_text]
    unimplemented = [req_id for req_id in req_ids if req_id not in src_text]

    orphan_files: list[str] = []
    for file_path in test_python_files:
        rel = file_path.resolve().relative_to(project_root.resolve())
        if rel.as_posix().startswith("tests/quality/QT_COMPLIANCE/"):
            continue
        test_id = _test_id_from_path(rel)
        if not test_id:
            continue
        if test_id not in tests_doc_text:
            orphan_files.append(rel.as_posix())

    report = {
        "requirement_count": len(req_ids),
        "untested_requirements": untested,
        "unimplemented_requirements": unimplemented,
        "orphan_test_files": orphan_files,
        "counts": {
            "untested_requirements": len(untested),
            "unimplemented_requirements": len(unimplemented),
            "orphan_test_files": len(orphan_files),
        },
    }

    output = project_root / "working" / "W25A-traceability-gaps.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert int(loaded["requirement_count"]) == len(req_ids), "Gap report requirement count mismatch"


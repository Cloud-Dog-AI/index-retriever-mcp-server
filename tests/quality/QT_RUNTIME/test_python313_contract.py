from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.QT
@pytest.mark.internal
@pytest.mark.req("FR-001")
def test_tests_execute_on_cpython_313() -> None:
    assert sys.implementation.name == "cpython"
    assert sys.version_info[:2] == (3, 13)


@pytest.mark.QT
@pytest.mark.internal
@pytest.mark.req("FR-001")
def test_project_and_container_runtime_contract_is_python_313() -> None:
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.13.14"
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["requires-python"] == ">=3.13,<3.14"
    assert pyproject["tool"]["ruff"]["target-version"] == "py313"
    assert pyproject["tool"]["mypy"]["python_version"] == "3.13"
    internal_dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert (
        "registry.cloud-dog.net:443/cloud-dog/python-runtime:3.13-slim-20260713"
        "@sha256:e23c4110eb0c8a2995635a97dee0fff83d5b729de611dfb1e31850c67b33ec60"
        in internal_dockerfile
    )
    public_dockerfile = (ROOT / "Dockerfile.public").read_text(encoding="utf-8")
    assert "python:3.13-slim" in public_dockerfile
    for dockerfile in (internal_dockerfile, public_dockerfile):
        assert "python3.13/site-packages" in dockerfile
        assert "python:3.12" not in dockerfile

# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""WSC-014 build-identity /version + runtime-config contract (W28E-1863 fix-wave-c).

Exercises the REAL build_web_app() (the public web tier that serves the SPA) over
Starlette TestClient and asserts:
- GET /version emits build/deploy identity (source_commit/build_date) as 200 JSON,
  NOT shadowed by the SPA catch-all @app.get("/{path:path}").
- GET /runtime-config.js carries the SAME identity as GIT_COMMIT / BUILD_DATE.
- A dev/source run (no CLOUD_DOG__INDEX__UI__* build ENV) falls back to git HEAD.

Build values reach the runtime as CLOUD_DOG__INDEX__UI__GIT_COMMIT /
CLOUD_DOG__INDEX__UI__BUILD_DATE env keys and are consumed via cloud_dog_config
(_runtime_override -> config.get) — RULES §1.4.1: zero direct os.environ added.

Each scenario runs in its OWN subprocess so cloud_dog_config compiles a clean
process-global config snapshot per scenario (in-process re-import leaks the snapshot).
The REAL build_web_app()/TestClient runs each time — this is harness hygiene only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# @pytest.mark.UT — unit tier (in-process ASGI, no external systems)
# @pytest.mark.webui — /version + runtime-config.js are WebUI About-page surfaces (WSC-014)
# @pytest.mark.req('FR-017') — thin web surface / SPA delivery (build-identity provenance)
pytestmark = [
    pytest.mark.UT,
    pytest.mark.webui,
    pytest.mark.req("FR-017"),
]

_REPO_ROOT = Path(__file__).resolve().parents[3]

_CHILD = r"""
import os, sys, json
from pathlib import Path
ROOT = Path(r"{root}")
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)
from starlette.testclient import TestClient
from index_server.web_server import build_web_app
client = TestClient(build_web_app())
v = client.get("/version")
rc = client.get("/runtime-config.js")
print("RESULT " + json.dumps({{
    "vstatus": v.status_code,
    "vctype": v.headers.get("content-type", ""),
    "vbody": v.json(),
    "rcstatus": rc.status_code,
    "rcbody": rc.text,
}}))
"""


def _probe(extra_env: dict[str, str]) -> dict:
    env = dict(os.environ)
    for key in (
        "CLOUD_DOG__INDEX__UI__GIT_COMMIT",
        "CLOUD_DOG__INDEX__UI__BUILD_DATE",
        "CLOUD_DOG__INDEX__UI__SOURCE_BRANCH",
    ):
        env.pop(key, None)
    env.update(extra_env)
    out = subprocess.run(
        [sys.executable, "-c", _CHILD.format(root=str(_REPO_ROOT))],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_REPO_ROOT),
    )
    for line in out.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):])
    raise AssertionError(f"child produced no RESULT:\nSTDOUT={out.stdout[-800:]}\nSTDERR={out.stderr[-2000:]}")


def test_version_and_runtime_config_emit_injected_identity() -> None:
    res = _probe(
        {
            "CLOUD_DOG__INDEX__UI__GIT_COMMIT": "cafe1234beefcafe1234beefcafe1234beefcafe",
            "CLOUD_DOG__INDEX__UI__BUILD_DATE": "2026-07-08T09:08:07Z",
            "CLOUD_DOG__INDEX__UI__SOURCE_BRANCH": "w28e-1863-idx",
        }
    )
    assert res["vstatus"] == 200
    assert "application/json" in res["vctype"]
    v = res["vbody"]
    assert v["source_commit"] == "cafe1234beefcafe1234beefcafe1234beefcafe"
    assert v["build_date"] == "2026-07-08T09:08:07Z"
    assert v["source_branch"] == "w28e-1863-idx"
    assert v["commit"] == v["source_commit"]
    assert v["service"] == "index-retriever-mcp-server"
    # runtime-config.js carries the SAME identity the About page already reads.
    assert res["rcstatus"] == 200
    assert '"GIT_COMMIT": "cafe1234beefcafe1234beefcafe1234beefcafe"' in res["rcbody"]
    assert '"BUILD_DATE": "2026-07-08T09:08:07Z"' in res["rcbody"]


def test_version_falls_back_to_git_head() -> None:
    head = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    res = _probe({})
    assert res["vstatus"] == 200
    assert res["vbody"]["source_commit"] == head


def test_version_not_shadowed_by_spa() -> None:
    res = _probe({})
    assert res["vstatus"] == 200
    assert "application/json" in res["vctype"]
    assert "text/html" not in res["vctype"]

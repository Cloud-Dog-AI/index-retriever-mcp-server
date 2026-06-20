# W28C-1715 — Index-retriever WebUI canonical @cloud-dog/ui CW-T*/CW-F*
# data-testid contract (PS-77).
#
# The merged @cloud-dog/ui package (ui-monorepo origin/main 39d7571) tags its
# canonical components with stable data-testid values: CW-T1 (DataTable root)
# and CW-F1 (EntityDialog root) among others. The index-retriever dashboard
# renders a DataTable (CW-T1); CRUD pages render an EntityDialog (CW-F1).
#
# These tests assert the contract two ways:
#   * an in-repo, infrastructure-free static assertion that the rebuilt and
#     shipped ui/dist bundle (the exact bytes baked into the container image)
#     carries CW-T1 and CW-F1; and
#   * a live Playwright assertion (delegated to the monorepo dashboard spec,
#     which performs page.getByTestId("CW-T1") on the rendered dashboard).

from __future__ import annotations

from pathlib import Path

import pytest

from tests.application._webui_playwright import run_playwright_spec

_UI_DIST_ASSETS = (
    Path(__file__).resolve().parents[3] / "ui" / "dist" / "assets"
)


def _shipped_bundle_text() -> str:
    js_files = sorted(_UI_DIST_ASSETS.glob("index-*.js"))
    assert js_files, f"no built WebUI JS bundle under {_UI_DIST_ASSETS}"
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in js_files)


@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-004")
def test_webui_cw_testid_contract_in_shipped_bundle() -> None:
    """The shipped ui/dist bundle carries the canonical CW-T1/CW-F1 test ids."""
    bundle = _shipped_bundle_text()
    assert "CW-T1" in bundle, "CW-T1 (DataTable root) missing from shipped WebUI bundle"
    assert "CW-F1" in bundle, "CW-F1 (EntityDialog root) missing from shipped WebUI bundle"


@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-004")
def test_webui_cw_t1_dashboard_get_by_test_id() -> None:
    """Live dashboard renders get_by_test_id('CW-T1') (delegated monorepo spec)."""
    run_playwright_spec("health-auth.spec.ts")

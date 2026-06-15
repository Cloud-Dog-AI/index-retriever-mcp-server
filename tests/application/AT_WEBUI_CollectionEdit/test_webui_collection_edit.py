from tests.application._webui_playwright import run_playwright_spec
import pytest
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-004")


def test_webui_collection_edit() -> None:
    run_playwright_spec('collection-edit.spec.ts')

from tests.application._webui_playwright import run_playwright_spec
import pytest
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-004")


def test_webui_file_upload() -> None:
    run_playwright_spec('upload-index-search.spec.ts')

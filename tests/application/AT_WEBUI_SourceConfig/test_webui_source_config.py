from tests.application._webui_playwright import run_playwright_spec
import pytest
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-004")


def test_webui_source_config() -> None:
    run_playwright_spec('source-config.spec.ts')

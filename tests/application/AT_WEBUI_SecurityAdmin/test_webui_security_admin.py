from tests.application._webui_playwright import run_playwright_spec
import pytest
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-004")
@pytest.mark.req("FR-018")


def test_webui_security_admin() -> None:
    run_playwright_spec('security-admin.spec.ts')

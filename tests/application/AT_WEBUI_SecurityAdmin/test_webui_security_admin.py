from tests.application._webui_playwright import run_playwright_spec


def test_webui_security_admin() -> None:
    run_playwright_spec('security-admin.spec.ts')

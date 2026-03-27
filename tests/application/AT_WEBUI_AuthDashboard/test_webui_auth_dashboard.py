from tests.application._webui_playwright import run_playwright_spec


def test_webui_auth_dashboard() -> None:
    run_playwright_spec('health-auth.spec.ts')

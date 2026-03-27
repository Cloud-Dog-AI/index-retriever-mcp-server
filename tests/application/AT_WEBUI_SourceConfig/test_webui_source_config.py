from tests.application._webui_playwright import run_playwright_spec


def test_webui_source_config() -> None:
    run_playwright_spec('source-config.spec.ts')

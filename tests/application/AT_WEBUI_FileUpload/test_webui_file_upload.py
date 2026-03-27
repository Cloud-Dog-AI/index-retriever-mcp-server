from tests.application._webui_playwright import run_playwright_spec


def test_webui_file_upload() -> None:
    run_playwright_spec('upload-index-search.spec.ts')

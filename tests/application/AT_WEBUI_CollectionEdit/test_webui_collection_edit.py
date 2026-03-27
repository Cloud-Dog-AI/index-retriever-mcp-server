from tests.application._webui_playwright import run_playwright_spec


def test_webui_collection_edit() -> None:
    run_playwright_spec('collection-edit.spec.ts')

from tests.application._webui_playwright import run_playwright_spec


def test_webui_collection_crud() -> None:
    run_playwright_spec('collection-crud.spec.ts')

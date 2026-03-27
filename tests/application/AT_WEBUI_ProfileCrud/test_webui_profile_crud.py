from tests.application._webui_playwright import run_playwright_spec


def test_webui_profile_crud() -> None:
    run_playwright_spec('profile-crud.spec.ts')

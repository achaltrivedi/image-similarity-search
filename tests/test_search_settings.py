from core.search_settings import (
    DEFAULT_SEARCH_SETTINGS,
    build_effective_search_settings,
    normalize_search_settings,
)


def test_normalize_search_settings_allows_zero_results_per_page():
    settings = normalize_search_settings({"default_results_per_page": 0})

    assert settings["default_results_per_page"] == 0


def test_build_effective_search_settings_preserves_zero_results_per_page_override():
    settings = build_effective_search_settings(
        DEFAULT_SEARCH_SETTINGS,
        {"default_results_per_page": 0},
    )

    assert settings["default_results_per_page"] == 0

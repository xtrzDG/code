"""
The demo page previews the widget in any language of its text bundles
(`?lang=`) and in either theme (`?theme=`), the way an owner checks it.
"""

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.widget_script_routes import build_widget_script_router
from app.utilities.channels.channel_endpoints import WIDGET_DEMO_PATH
from tests.channels.widget_script_source import (
    BUSINESS_ID,
    SCRIPT_SOURCE,
    parse_script_tags,
)


def demo(params: dict[str, str]) -> tuple[str, dict[str, str | None]]:
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(build_widget_script_router())
    response = TestClient(http_application).get(
        WIDGET_DEMO_PATH, params={"business_id": BUSINESS_ID, **params}
    )
    assert response.status_code == 200
    [widget_tag] = parse_script_tags(response.text)
    return response.text, widget_tag


@pytest.mark.parametrize(("lang", "page"), [("ka", "ka"), ("he", "en"), ("ru", "ru")])
def test_lang_forces_the_widget_language_and_the_page_follows_when_it_can(
    lang: str, page: str
) -> None:
    markup, widget_tag = demo({"lang": lang})

    assert widget_tag["data-language"] == lang
    assert f'<html lang="{page}">' in markup


def test_every_widget_bundle_language_can_be_previewed() -> None:
    bundle = SCRIPT_SOURCE[SCRIPT_SOURCE.index("var TEXTS = {") :]
    languages = re.findall(r"\n    ([a-z]+): \{", bundle[: bundle.index("\n  };")])

    for language in languages:
        assert demo({"lang": language})[1]["data-language"] == language


def test_language_wins_over_lang() -> None:
    assert demo({"language": "ru", "lang": "ka"})[1]["data-language"] == "ru"


@pytest.mark.parametrize("theme", ["dark", "light", "Dark"])
def test_theme_previews_the_widget_in_light_or_dark(theme: str) -> None:
    assert demo({"theme": theme})[1]["data-theme"] == theme.lower()


@pytest.mark.parametrize("theme", ["sepia", "", "<b>"])
def test_any_other_theme_follows_the_visitors_system(theme: str) -> None:
    assert "data-theme" not in demo({"theme": theme})[1]


def test_the_page_keeps_the_warm_palette_in_both_schemes() -> None:
    markup, _ = demo({})

    assert "--canvas: #f6f5f2" in markup
    assert "--canvas: #141311" in markup
    assert "--accent-solid: #ad5732" in markup

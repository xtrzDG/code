"""The website chat demo page speaks the cabinet's languages and its palette."""

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.widget_demo_page import EXAMPLE_ACCENT_COLOR, demo_page_language
from app.gateways.http.widget_demo_texts import WIDGET_DEMO_TEXTS
from app.gateways.http.widget_script_routes import build_widget_script_router
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_endpoints import WIDGET_DEMO_PATH
from tests.channels.widget_script_source import BUSINESS_ID, parse_script_tags


def build_client() -> TestClient:
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(build_widget_script_router())
    return TestClient(http_application)


def page_language(markup: str) -> str:
    match = re.search(r'<html lang="([^"]+)">', markup)
    assert match is not None
    return match.group(1)


class TestPageLanguage:
    @pytest.mark.parametrize("language", ["en", "ru", "ka"])
    def test_the_browser_language_picks_the_page_texts(self, language: str) -> None:
        response = build_client().get(
            WIDGET_DEMO_PATH,
            params={"business_id": BUSINESS_ID},
            headers={"Accept-Language": f"{language}-GE,{language};q=0.9,en;q=0.5"},
        )

        texts = WIDGET_DEMO_TEXTS[language]
        assert response.status_code == 200
        assert page_language(response.text) == language
        assert response.headers["content-language"] == language
        assert f"<h1>{texts.heading}</h1>" in response.text
        assert texts.embed_title in response.text
        assert texts.option_open in response.text
        [widget_tag] = parse_script_tags(response.text)
        # The widget still picks its own language among the business languages.
        assert "data-language" not in widget_tag

    def test_a_forced_widget_language_also_sets_the_page_language(self) -> None:
        response = build_client().get(
            WIDGET_DEMO_PATH,
            params={"business_id": BUSINESS_ID, "language": "ka"},
            headers={"Accept-Language": "ru"},
        )

        assert page_language(response.text) == "ka"
        [widget_tag] = parse_script_tags(response.text)
        assert widget_tag["data-language"] == "ka"

    def test_other_languages_read_the_page_in_the_browser_language(self) -> None:
        assert demo_page_language(LanguageTag("he"), "ru-RU,ru;q=0.9") == "ru"
        assert demo_page_language(LanguageTag("he"), None) == "en"
        assert demo_page_language(None, "de-DE,fr;q=0.8") == "en"
        assert demo_page_language(None, "not a header;;") == "en"
        assert demo_page_language(LanguageTag("ru-RU"), None) == "ru"

    def test_the_form_asks_for_the_business_in_the_page_language(self) -> None:
        response = build_client().get(
            WIDGET_DEMO_PATH, headers={"Accept-Language": "ru"}
        )

        texts = WIDGET_DEMO_TEXTS["ru"]
        assert page_language(response.text) == "ru"
        assert texts.business_id_label in response.text
        assert texts.show_button in response.text
        assert 'name="language"' not in response.text


class TestPagePalette:
    def test_the_example_colour_and_the_button_are_the_clay_accent(self) -> None:
        response = build_client().get(
            WIDGET_DEMO_PATH, params={"business_id": BUSINESS_ID}
        )

        assert EXAMPLE_ACCENT_COLOR == "#ad5732"
        assert f"data-color=&quot;{EXAMPLE_ACCENT_COLOR}&quot;" in response.text
        assert "--accent-solid: #ad5732" in response.text
        lowered = response.text.lower()
        for retired in ("#0f766e", "#4f46e5", "#0b1120", "#111827"):
            assert retired not in lowered

    def test_texts_are_escaped(self) -> None:
        response = build_client().get(
            WIDGET_DEMO_PATH,
            params={"business_id": BUSINESS_ID},
            headers={"Accept-Language": "en"},
        )

        assert "closing &lt;/body&gt; tag" in response.text
        assert "&lt;your API address&gt;/widget.js" in response.text

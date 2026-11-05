"""
Starter chips in every language of the chat: a language the FAQ has no
question in gets the niche's ready questions (en, ru, ka), never a chip
in another language.
"""

from typing import Any

from app.registries.niches.starter_answer_registry import StarterAnswerRegistry
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.channels.widget import WidgetStarterQuestionView
from app.schemas.typings.channels.strings import WidgetStarterQuestionText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.utilities.channels.widget_starters import add_niche_starters
from tests.e2e.harness import Workshop
from tests.sharing.test_widget_handoff_api import open_web_chat

RESTAURANT_FAQ = StarterAnswerRegistry().get(NicheKey.RESTAURANT, CountryCode("GE")).faq


def chip(language: str, text: str) -> WidgetStarterQuestionView:
    return WidgetStarterQuestionView(
        language=LanguageTag(language), text=WidgetStarterQuestionText(text)
    )


def test_languages_without_faq_questions_get_the_niches_ready_ones() -> None:
    from_faq = [chip("ru", "Есть ли парковка?")]
    languages = [LanguageTag(tag) for tag in ("ka", "ru", "en", "he")]

    starters = add_niche_starters(from_faq, languages, RESTAURANT_FAQ)

    by_language: dict[str, list[str]] = {}
    for starter in starters:
        by_language.setdefault(str(starter.language), []).append(str(starter.text))
    # Russian keeps the owner's own question only; Hebrew has no niche text.
    assert by_language == {
        "ru": ["Есть ли парковка?"],
        "ka": ["როგორ დავჯავშნო მაგიდა?", by_language["ka"][1]],
        "en": ["How can I book a table?", by_language["en"][1]],
    }
    # Only questions with a ready answer: never "Is there parking nearby?".
    assert "Is there parking nearby?" not in by_language["en"]


def test_at_most_three_per_language_and_none_longer_than_a_chip() -> None:
    starters = add_niche_starters([], [LanguageTag("en")], RESTAURANT_FAQ * 3)

    assert len(starters) == 3
    assert all(len(str(starter.text)) <= 80 for starter in starters)


def test_the_hosted_page_gets_chips_in_its_three_languages(workshop: Workshop) -> None:
    restaurant = open_web_chat(workshop)

    config: dict[str, Any] = workshop.client.get(
        f"/v1/widget/{restaurant.business_id}/config"
    ).json()

    languages = {starter["language"] for starter in config["starter_questions"]}
    assert {language["tag"] for language in config["languages"]} <= languages | {"he"}
    assert {"en", "ru", "ka"} <= languages

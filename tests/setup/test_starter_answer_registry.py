"""The niche starter answers: every niche, three owner languages, any country."""

import pytest

from app.registries.niches import starter_answer_registry
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.niches.starter_answer_registry import (
    StarterAnswerRegistry,
    find_weekend,
    lay_over_week,
)
from app.registries.niches.starters.starter_catalog import NICHE_STARTERS
from app.registries.niches.starters.starter_parts import at, opening
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.setup.starter_catalog import (
    NicheStarterDefinition,
    StarterOfferDefinition,
)
from app.schemas.typings.localization.constrained_strings import CountryCode

OWNER_LANGUAGES: tuple[str, ...] = ("en", "ru", "ka")


def assert_in_owner_languages(text: LocalizedText) -> None:
    by_language = {str(key): str(value) for key, value in text.values.items()}
    for language in OWNER_LANGUAGES:
        assert by_language.get(language, "").strip(), (language, by_language)


def all_texts(definition: NicheStarterDefinition) -> list[LocalizedText]:
    texts: list[LocalizedText] = [definition.tones]
    if definition.booking is not None:
        texts.append(definition.booking.cancellation_policies)
    if definition.resource is not None:
        texts.append(definition.resource.names)
    for question in definition.faq:
        texts.append(question.questions)
        if question.answers is not None:
            texts.append(question.answers)
    texts.extend(example.titles for example in definition.offers)
    return texts


def test_every_niche_has_starter_answers_in_every_owner_language() -> None:
    registry = StarterAnswerRegistry()

    assert {definition.niche_key for definition in NICHE_STARTERS} == set(NicheKey)
    for definition in NICHE_STARTERS:
        answers = registry.get(definition.niche_key, CountryCode("GE"))
        assert answers.niche_key is definition.niche_key
        assert answers.hours != [], definition.niche_key
        assert definition.faq != [], definition.niche_key
        assert definition.offers != [], definition.niche_key
        assert any(question.answers is not None for question in definition.faq)
        for text in all_texts(definition):
            assert_in_owner_languages(text)


def test_niches_that_take_bookings_suggest_booking_rules_and_a_resource() -> None:
    templates = NicheTemplateRegistry()

    for definition in NICHE_STARTERS:
        if templates.get(definition.niche_key).takes_bookings:
            assert definition.booking is not None, definition.niche_key
            assert definition.resource is not None, definition.niche_key


def test_frequent_questions_and_offer_examples_have_unique_keys() -> None:
    for definition in NICHE_STARTERS:
        faq_keys = [str(question.key) for question in definition.faq]
        offer_keys = [str(example.key) for example in definition.offers]
        assert len(faq_keys) == len(set(faq_keys)), definition.niche_key
        assert len(offer_keys) == len(set(offer_keys)), definition.niche_key


def test_offer_examples_never_carry_a_price() -> None:
    assert "price_minor" not in StarterOfferDefinition.model_fields
    assert not any(
        "price" in field_name for field_name in StarterOfferDefinition.model_fields
    )


@pytest.mark.parametrize(
    ("country", "weekend"),
    [
        ("GE", {Weekday.SATURDAY, Weekday.SUNDAY}),
        ("DE", {Weekday.SATURDAY, Weekday.SUNDAY}),
        ("IL", {Weekday.FRIDAY, Weekday.SATURDAY}),
        ("AE", {Weekday.SATURDAY, Weekday.SUNDAY}),
        ("IR", {Weekday.FRIDAY}),
        ("IN", {Weekday.SUNDAY}),
    ],
)
def test_the_weekend_comes_from_the_country(
    country: str, weekend: set[Weekday]
) -> None:
    assert find_weekend(CountryCode(country)) == frozenset(weekend)


def test_hours_rest_on_the_weekend_of_the_business_country() -> None:
    registry = StarterAnswerRegistry()

    in_israel = registry.get(NicheKey.CLINIC, CountryCode("IL")).hours
    in_georgia = registry.get(NicheKey.CLINIC, CountryCode("GE")).hours

    # A clinic works 9:00-19:00 on working days and 10:00-15:00 on the weekend.
    short_days_in_israel = [
        int(day.weekday) for day in in_israel if day.opens_at == 600
    ]
    short_days_in_georgia = [
        int(day.weekday) for day in in_georgia if day.opens_at == 600
    ]
    assert short_days_in_israel == [5, 6]
    assert short_days_in_georgia == [6, 7]
    assert len(in_israel) == len(in_georgia) == 7


def test_a_week_is_laid_over_working_days_and_the_weekend() -> None:
    week = lay_over_week(
        opening((at(9), at(18)), (at(10), at(14))),
        frozenset({Weekday.FRIDAY, Weekday.SATURDAY}),
    )
    closed_on_weekend = lay_over_week(
        opening((at(9), at(18)), None),
        frozenset({Weekday.SATURDAY, Weekday.SUNDAY}),
    )

    assert [(int(day.weekday), day.opens_at, day.closes_at) for day in week] == [
        (1, 540, 1080),
        (2, 540, 1080),
        (3, 540, 1080),
        (4, 540, 1080),
        (5, 600, 840),
        (6, 600, 840),
        (7, 540, 1080),
    ]
    assert [int(day.weekday) for day in closed_on_weekend] == [1, 2, 3, 4, 5]


def test_the_registry_refuses_a_niche_twice_or_a_niche_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        starter_answer_registry,
        "NICHE_STARTERS",
        (*NICHE_STARTERS, NICHE_STARTERS[0]),
    )
    with pytest.raises(ValueError, match="two starters"):
        StarterAnswerRegistry()

    monkeypatch.setattr(starter_answer_registry, "NICHE_STARTERS", NICHE_STARTERS[1:])
    with pytest.raises(ValueError, match="without starter answers"):
        StarterAnswerRegistry()

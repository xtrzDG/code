"""
Which texts of a niche template an admin may reword: exactly the niche's
owner-facing texts of the catalog and its starter answers' texts; never a
key, a type, a required flag, a number or a text of every niche.
"""

import json
from pathlib import Path

import pytest

from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.niches.starter_answer_registry import StarterAnswerRegistry
from app.schemas.constants.niches import (
    NicheKey,
    NicheTextSection,
    QuestionAnswerType,
)
from app.schemas.dto.niche_texts.niche_text_fields import NicheTextCatalog
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.localization.owner_texts import OWNER_TEXTS_DIRECTORY
from app.utilities.niches.niche_text_catalog import build_niche_text_catalog

TEMPLATES = NicheTemplateRegistry()
STARTERS = StarterAnswerRegistry()
ENGLISH_TEXTS: dict[str, str] = json.loads(
    Path(OWNER_TEXTS_DIRECTORY / "en.json").read_text(encoding="utf-8")
)["texts"]


def catalog_of(niche: NicheKey) -> NicheTextCatalog:
    return build_niche_text_catalog(
        TEMPLATES.get(niche), STARTERS.get(niche, CountryCode("GE"))
    )


@pytest.mark.parametrize("niche", list(NicheKey))
def test_the_template_fields_are_the_niches_own_catalog_texts(niche: NicheKey) -> None:
    prefix = f"niches.{niche.value}."
    catalog_fields = {
        key.removeprefix(prefix) for key in ENGLISH_TEXTS if key.startswith(prefix)
    }
    template_fields = {
        str(field.field_key)
        for field in catalog_of(niche).fields
        if field.section is not NicheTextSection.STARTERS
    }

    assert template_fields == catalog_fields


@pytest.mark.parametrize("niche", list(NicheKey))
def test_every_starter_text_is_editable_and_nothing_else_of_the_starters(
    niche: NicheKey,
) -> None:
    starters = STARTERS.get(niche, CountryCode("GE"))
    expected = {"starters.tone"}
    if starters.booking is not None:
        expected.add("starters.cancellation_policy")
    if starters.resource is not None:
        expected.add("starters.resource_name")
    for faq in starters.faq:
        expected.add(f"starters.faq.{faq.key}.question")
        if faq.answers is not None:
            expected.add(f"starters.faq.{faq.key}.answer")
    expected |= {f"starters.offers.{offer.key}.title" for offer in starters.offers}

    assert {
        str(field.field_key)
        for field in catalog_of(niche).fields
        if field.section is NicheTextSection.STARTERS
    } == expected


@pytest.mark.parametrize("niche", list(NicheKey))
def test_every_code_text_fits_its_field_and_names_english(niche: NicheKey) -> None:
    for field in catalog_of(niche).fields:
        assert "en" in {str(language) for language in field.code_texts.values}
        for value in field.code_texts.values.values():
            assert len(value) <= int(field.max_length), field.field_key


def test_the_questions_keep_their_structure_and_name_their_fields() -> None:
    template = TEMPLATES.get(NicheKey.RESTAURANT)
    catalog = catalog_of(NicheKey.RESTAURANT)

    assert [question.key for question in catalog.questions] == [
        question.key for question in template.questions
    ]
    cuisine = catalog.questions[0]
    assert str(cuisine.label_field) == "questions.cuisine.label"
    assert str(cuisine.hint_field) == "questions.cuisine.hint"
    assert cuisine.is_required is True
    banquets = next(q for q in catalog.questions if str(q.key) == "banquets")
    assert [str(choice.field_key) for choice in banquets.choices] == [
        "questions.banquets.choices.no",
        "questions.banquets.choices.separate_hall",
        "questions.banquets.choices.whole_venue",
    ]


def test_the_common_yes_and_no_are_shown_but_never_reworded_per_niche() -> None:
    catalog = catalog_of(NicheKey.RESTAURANT)
    kids_menu = next(q for q in catalog.questions if str(q.key) == "kids_menu")

    assert kids_menu.answer_type is QuestionAnswerType.YES_NO
    assert [choice.field_key for choice in kids_menu.choices] == [None, None]
    assert [
        str(choice.fixed_labels.values[next(iter(choice.fixed_labels.values))])
        for choice in kids_menu.choices
        if choice.fixed_labels is not None
    ] == ["Yes", "No"]
    assert not any(
        str(field.field_key).startswith("questions.kids_menu.choices")
        for field in catalog.fields
    )


def test_rules_are_editable_line_by_line_without_the_platforms_own() -> None:
    catalog = catalog_of(NicheKey.RESTAURANT)
    rules = [
        str(field.field_key)
        for field in catalog.fields
        if field.section is NicheTextSection.RULES
    ]

    assert rules == [
        "handoff_rules.1",
        "handoff_rules.2",
        "handoff_rules.3",
        "forbidden_rules.1",
    ]
    assert all(
        int(field.max_length) == 300
        for field in catalog.fields
        if field.section is NicheTextSection.RULES
    )

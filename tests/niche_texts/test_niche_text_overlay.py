"""
The effective template: the code template with an override set laid over
its texts. Without overrides nothing changes (the same objects); with them
only the words change, never a key, a type, a flag, a choice or a number.
"""

import pytest

from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.niches.starter_answer_registry import StarterAnswerRegistry
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.niche_texts import NicheTextEntry
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.utilities.niches.niche_text_catalog import build_niche_text_catalog
from app.utilities.niches.niche_text_overlay import (
    overlay_niche_template,
    overlay_starter_answers,
)

TEMPLATES = NicheTemplateRegistry()
STARTERS = StarterAnswerRegistry()
GE = CountryCode("GE")
RU = LanguageTag("ru")
EN = LanguageTag("en")
HE = LanguageTag("he")


def entry(field: str, text: str, language: LanguageTag = RU) -> NicheTextEntry:
    return NicheTextEntry(
        field_key=NicheTextFieldKey(field),
        language=language,
        text=NicheOverrideText(text),
    )


def structure(template: NicheTemplate) -> object:
    """Everything of a template that is not an owner-facing text."""

    return template.model_dump(
        exclude={
            "names",
            "descriptions",
            "resource_nouns",
            "default_handoff_rules",
            "default_forbidden_rules",
        }
        | {"questions"}
    ), [
        (
            q.key,
            q.step,
            q.answer_type,
            q.is_required,
            q.fact_key,
            [c.key for c in q.choices],
        )
        for q in template.questions
    ]


@pytest.mark.parametrize("niche", list(NicheKey))
def test_without_overrides_the_code_template_comes_back_unchanged(
    niche: NicheKey,
) -> None:
    template = TEMPLATES.get(niche)
    starters = STARTERS.get(niche, GE)

    assert overlay_niche_template(template, []) is template
    assert overlay_starter_answers(starters, []) is starters
    # Overrides of starters only leave the template as it was, and back.
    assert overlay_niche_template(template, [entry("starters.tone", "Тон")]) == template
    assert overlay_starter_answers(starters, [entry("name", "Имя")]) is starters


@pytest.mark.parametrize("niche", list(NicheKey))
def test_overriding_every_text_changes_only_words(niche: NicheKey) -> None:
    template = TEMPLATES.get(niche)
    starters = STARTERS.get(niche, GE)
    catalog = build_niche_text_catalog(template, starters)
    entries = [
        entry(str(field.field_key), f"Свой текст {position}")
        for position, field in enumerate(catalog.fields)
    ]

    effective = overlay_niche_template(template, entries)
    effective_starters = overlay_starter_answers(starters, entries)

    assert structure(effective) == structure(template)
    assert effective.questions[0].labels.values[RU].startswith("Свой текст")
    # English, the prompt's language, keeps the code's words.
    assert (
        effective.questions[0].labels.values[EN]
        == template.questions[0].labels.values[EN]
    )
    assert (
        effective.default_handoff_rules.values[EN]
        == template.default_handoff_rules.values[EN]
    )
    assert effective_starters.hours == starters.hours
    assert effective_starters.tones.values[RU].startswith("Свой текст")
    assert [offer.kind for offer in effective_starters.offers] == [
        offer.kind for offer in starters.offers
    ]


def test_one_label_in_one_language_changes_only_that_label() -> None:
    template = TEMPLATES.get(NicheKey.RESTAURANT)

    effective = overlay_niche_template(
        template, [entry("questions.cuisine.label", "Какую кухню вы готовите?")]
    )

    assert str(effective.questions[0].labels.values[RU]) == "Какую кухню вы готовите?"
    assert effective.questions[0].hints == template.questions[0].hints
    assert effective.questions[1:] == template.questions[1:]
    assert effective.names == template.names
    assert effective.default_handoff_rules == template.default_handoff_rules


def test_a_language_the_code_lacks_is_added_for_that_text() -> None:
    starters = STARTERS.get(NicheKey.RESTAURANT, GE)
    assert HE not in starters.tones.values

    effective = overlay_starter_answers(
        starters, [entry("starters.tone", "חם וקצר", HE)]
    )

    assert str(effective.tones.values[HE]) == "חם וקצר"
    assert effective.tones.values[EN] == starters.tones.values[EN]


def test_a_rule_line_is_replaced_in_its_list_and_the_platforms_rules_stay_first() -> (
    None
):
    template = TEMPLATES.get(NicheKey.RESTAURANT)

    effective = overlay_niche_template(
        template,
        [
            entry("handoff_rules.2", "Банкет или группа больше 25 человек"),
            entry("forbidden_rules.1", "Никаких обещаний об аллергенах"),
        ],
    )

    handoff = str(effective.default_handoff_rules.values[RU]).split("\n")
    code_handoff = str(template.default_handoff_rules.values[RU]).split("\n")
    assert handoff == [
        code_handoff[0],
        "Банкет или группа больше 25 человек",
        code_handoff[2],
    ]
    forbidden = str(effective.default_forbidden_rules.values[RU]).split("\n")
    code_forbidden = str(template.default_forbidden_rules.values[RU]).split("\n")
    assert forbidden == [*code_forbidden[:-1], "Никаких обещаний об аллергенах"]
    assert (
        effective.default_forbidden_rules.values[EN]
        == template.default_forbidden_rules.values[EN]
    )


def test_an_entry_of_a_field_the_code_dropped_is_ignored() -> None:
    template = TEMPLATES.get(NicheKey.RESTAURANT)
    starters = STARTERS.get(NicheKey.RESTAURANT, GE)

    assert (
        overlay_niche_template(
            template, [entry("questions.gone.label", "Нет такого вопроса")]
        )
        == template
    )
    assert (
        overlay_starter_answers(
            starters, [entry("starters.faq.gone.question", "Нет такого")]
        )
        == starters
    )

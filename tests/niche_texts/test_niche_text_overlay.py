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
IT = LanguageTag("it")
EN = LanguageTag("en")


def entry(field: str, text: str, language: LanguageTag = IT) -> NicheTextEntry:
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
    assert (
        overlay_niche_template(template, [entry("starters.tone", "Tono")]) == template
    )
    assert overlay_starter_answers(starters, [entry("name", "Nome")]) is starters


@pytest.mark.parametrize("niche", list(NicheKey))
def test_overriding_every_text_changes_only_words(niche: NicheKey) -> None:
    template = TEMPLATES.get(niche)
    starters = STARTERS.get(niche, GE)
    catalog = build_niche_text_catalog(template, starters)
    entries = [
        entry(str(field.field_key), f"Testo proprio {position}")
        for position, field in enumerate(catalog.fields)
    ]

    effective = overlay_niche_template(template, entries)
    effective_starters = overlay_starter_answers(starters, entries)

    assert structure(effective) == structure(template)
    assert effective.questions[0].labels.values[IT].startswith("Testo proprio")
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
    assert effective_starters.tones.values[IT].startswith("Testo proprio")
    assert [offer.kind for offer in effective_starters.offers] == [
        offer.kind for offer in starters.offers
    ]


def test_one_label_in_one_language_changes_only_that_label() -> None:
    template = TEMPLATES.get(NicheKey.RESTAURANT)

    effective = overlay_niche_template(
        template, [entry("questions.cuisine.label", "Quale cucina proponete?")]
    )

    assert str(effective.questions[0].labels.values[IT]) == "Quale cucina proponete?"
    assert effective.questions[0].hints == template.questions[0].hints
    assert effective.questions[1:] == template.questions[1:]
    assert effective.names == template.names
    assert effective.default_handoff_rules == template.default_handoff_rules


def test_a_language_the_code_lacks_is_added_for_that_text() -> None:
    # The starter answers are still written in code (en, ru, ka), so Italian
    # is a language the code lacks until they move into the text catalog.
    starters = STARTERS.get(NicheKey.RESTAURANT, GE)
    assert IT not in starters.tones.values

    effective = overlay_starter_answers(
        starters, [entry("starters.tone", "Caldo e breve")]
    )

    assert str(effective.tones.values[IT]) == "Caldo e breve"
    assert effective.tones.values[EN] == starters.tones.values[EN]


def test_a_rule_line_is_replaced_in_its_list_and_the_platforms_rules_stay_first() -> (
    None
):
    template = TEMPLATES.get(NicheKey.RESTAURANT)

    effective = overlay_niche_template(
        template,
        [
            entry("handoff_rules.2", "Banchetto o gruppo di oltre 25 persone"),
            entry("forbidden_rules.1", "Nessuna promessa sugli allergeni"),
        ],
    )

    handoff = str(effective.default_handoff_rules.values[IT]).split("\n")
    code_handoff = str(template.default_handoff_rules.values[IT]).split("\n")
    assert handoff == [
        code_handoff[0],
        "Banchetto o gruppo di oltre 25 persone",
        code_handoff[2],
    ]
    forbidden = str(effective.default_forbidden_rules.values[IT]).split("\n")
    code_forbidden = str(template.default_forbidden_rules.values[IT]).split("\n")
    assert forbidden == [*code_forbidden[:-1], "Nessuna promessa sugli allergeni"]
    assert (
        effective.default_forbidden_rules.values[EN]
        == template.default_forbidden_rules.values[EN]
    )


def test_an_entry_of_a_field_the_code_dropped_is_ignored() -> None:
    template = TEMPLATES.get(NicheKey.RESTAURANT)
    starters = STARTERS.get(NicheKey.RESTAURANT, GE)

    assert (
        overlay_niche_template(
            template, [entry("questions.gone.label", "Nessuna domanda così")]
        )
        == template
    )
    assert (
        overlay_starter_answers(
            starters, [entry("starters.faq.gone.question", "Non esiste")]
        )
        == starters
    )

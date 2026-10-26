"""
The effective niche template: the code template with a published override
set laid over its owner-facing texts.

Only texts change; every key, type, flag, choice and number stays as the
code has it. Without an override the code's own objects come back
unchanged (the same instances), so a niche nobody edited reads exactly as
before. A rule list is rebuilt line by line the way the catalog builds it
(`owner_rule_lines`), so an override of one line in one language changes
only that line. An entry naming a field the code no longer has is ignored.
"""

from collections.abc import Mapping, Sequence

from app.schemas.domain.niche_texts import NicheTextEntry
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.niches import NicheTemplate, QuestionChoice, QuestionDefinition
from app.schemas.dto.setup.starter_catalog import (
    StarterAnswers,
    StarterFaqDefinition,
    StarterOfferDefinition,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.niches.constrained_strings import NicheTextFieldKey
from app.utilities.knowledge.localized_texts import join_rule_lines, join_rule_lists
from app.utilities.localization.owner_texts import (
    OWNER_TEXT_CATALOG,
    VALUE_ORDER,
    numbered_keys,
    owner_rule_lines,
    owner_text,
)
from app.utilities.niches.niche_text_keys import (
    CANCELLATION_POLICY_FIELD,
    COMMON_FORBIDDEN_RULES,
    DESCRIPTION_FIELD,
    FORBIDDEN_RULES,
    HANDOFF_RULES,
    NAME_FIELD,
    RESOURCE_NAME_FIELD,
    RESOURCE_NOUN_FIELD,
    STARTERS,
    TONE_FIELD,
    choice_field,
    faq_answer_field,
    faq_question_field,
    hint_field,
    label_field,
    niche_text_key,
    offer_title_field,
    rule_field,
)

type OverrideTexts = Mapping[
    NicheTextFieldKey, Mapping[LanguageTag, LocalizedTextValue]
]

LIST_LANGUAGES: tuple[LanguageTag, ...] = tuple(
    LanguageTag(language.value) for language in VALUE_ORDER
)


def override_texts(entries: Sequence[NicheTextEntry]) -> OverrideTexts:
    """The entries by field, then by language."""

    texts: dict[NicheTextFieldKey, dict[LanguageTag, LocalizedTextValue]] = {}
    for entry in entries:
        texts.setdefault(entry.field_key, {})[entry.language] = LocalizedTextValue(
            str(entry.text)
        )

    return texts


def overlay(
    text: LocalizedText, values: Mapping[LanguageTag, LocalizedTextValue] | None
) -> LocalizedText:
    """`text` with the given languages replaced or added."""

    if not values:
        return text

    return LocalizedText(values={**text.values, **values})


def overlay_niche_template(
    template: NicheTemplate, entries: Sequence[NicheTextEntry]
) -> NicheTemplate:
    """The template as owners read it with these overrides."""

    texts: OverrideTexts = override_texts(entries)
    if not texts:
        return template

    return template.model_copy(
        update={
            "names": overlay(template.names, texts.get(NAME_FIELD)),
            "descriptions": overlay(
                template.descriptions, texts.get(DESCRIPTION_FIELD)
            ),
            "resource_nouns": overlay(
                template.resource_nouns, texts.get(RESOURCE_NOUN_FIELD)
            ),
            "questions": [
                overlay_question(question, texts) for question in template.questions
            ],
            "default_handoff_rules": overlay_rule_list(
                template, HANDOFF_RULES, texts, template.default_handoff_rules
            ),
            "default_forbidden_rules": overlay_rule_list(
                template, FORBIDDEN_RULES, texts, template.default_forbidden_rules
            ),
        }
    )


def overlay_question(
    question: QuestionDefinition, texts: OverrideTexts
) -> QuestionDefinition:
    choices: list[QuestionChoice] = [
        choice.model_copy(
            update={
                "labels": overlay(
                    choice.labels, texts.get(choice_field(question.key, choice.key))
                )
            }
        )
        for choice in question.choices
    ]
    return question.model_copy(
        update={
            "labels": overlay(question.labels, texts.get(label_field(question.key))),
            "hints": (
                None
                if question.hints is None
                else overlay(question.hints, texts.get(hint_field(question.key)))
            ),
            "choices": choices,
        }
    )


def overlay_rule_list(
    template: NicheTemplate,
    rules: str,
    texts: OverrideTexts,
    code_rules: LocalizedText,
) -> LocalizedText:
    """The niche's handoff or forbidden rules with their lines overridden."""

    prefix: str = f"{rules}."
    if not any(str(field_key).startswith(prefix) for field_key in texts):
        return code_rules

    keys = numbered_keys(niche_text_key(template.key, rules), OWNER_TEXT_CATALOG)
    own: LocalizedText = join_rule_lines(
        [
            overlay(owner_text(str(key)), texts.get(rule_field(rules, position)))
            for position, key in enumerate(keys, start=1)
        ],
        LIST_LANGUAGES,
    )
    if rules == FORBIDDEN_RULES:
        return join_rule_lists(owner_rule_lines(COMMON_FORBIDDEN_RULES), own)

    return own


def overlay_starter_answers(
    starters: StarterAnswers, entries: Sequence[NicheTextEntry]
) -> StarterAnswers:
    """The starter answers as a new owner is offered them with these overrides."""

    texts: OverrideTexts = override_texts(entries)
    if not any(str(field_key).startswith(f"{STARTERS}.") for field_key in texts):
        return starters

    booking = starters.booking
    resource = starters.resource
    return starters.model_copy(
        update={
            "tones": overlay(starters.tones, texts.get(TONE_FIELD)),
            "booking": (
                None
                if booking is None
                else booking.model_copy(
                    update={
                        "cancellation_policies": overlay(
                            booking.cancellation_policies,
                            texts.get(CANCELLATION_POLICY_FIELD),
                        )
                    }
                )
            ),
            "resource": (
                None
                if resource is None
                else resource.model_copy(
                    update={
                        "names": overlay(resource.names, texts.get(RESOURCE_NAME_FIELD))
                    }
                )
            ),
            "faq": [overlay_faq(faq, texts) for faq in starters.faq],
            "offers": [overlay_offer(offer, texts) for offer in starters.offers],
        }
    )


def overlay_faq(
    faq: StarterFaqDefinition, texts: OverrideTexts
) -> StarterFaqDefinition:
    return faq.model_copy(
        update={
            "questions": overlay(faq.questions, texts.get(faq_question_field(faq.key))),
            "answers": (
                None
                if faq.answers is None
                else overlay(faq.answers, texts.get(faq_answer_field(faq.key)))
            ),
        }
    )


def overlay_offer(
    offer: StarterOfferDefinition, texts: OverrideTexts
) -> StarterOfferDefinition:
    return offer.model_copy(
        update={
            "titles": overlay(offer.titles, texts.get(offer_title_field(offer.key)))
        }
    )

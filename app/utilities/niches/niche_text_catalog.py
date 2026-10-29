"""
Which texts of a niche template an admin may reword, read from the code.

Only words: the niche's name, description and what it books, each profile
question's label, hint and its own choices, the default handoff and
forbidden rules (line by line), and the starter answers (tone,
cancellation rule, first resource, frequent questions and answers, offer
examples). Keys, answer types, required flags, choices themselves,
validation, prompt rules, example exchanges, tools and every number stay
in code: the structure an owner fills in never changes.

The common yes/no choices and the platform's forbidden rules belong to
every niche, so no niche rewords them.
"""

from app.schemas.constants.niches import NicheKey, NicheTextSection
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.niche_texts.niche_text_fields import (
    NicheTextCatalog,
    NicheTextChoice,
    NicheTextField,
    NicheTextQuestion,
)
from app.schemas.dto.niches import NicheTemplate, QuestionDefinition
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.typings.niches.constrained_integers import NicheTextLengthLimit
from app.schemas.typings.niches.constrained_strings import NicheTextFieldKey
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.utilities.localization.owner_texts import (
    OWNER_TEXT_CATALOG,
    has_owner_text,
    numbered_keys,
    owner_text,
)
from app.utilities.niches.niche_text_keys import (
    CANCELLATION_POLICY_FIELD,
    CANCELLATION_POLICY_LIMIT,
    CHOICE_LIMIT,
    DESCRIPTION_FIELD,
    DESCRIPTION_LIMIT,
    FAQ_ANSWER_LIMIT,
    FAQ_QUESTION_LIMIT,
    FORBIDDEN_RULES,
    HANDOFF_RULES,
    HINT_LIMIT,
    LABEL_LIMIT,
    NAME_FIELD,
    NAME_LIMIT,
    OFFER_TITLE_LIMIT,
    RESOURCE_NAME_FIELD,
    RESOURCE_NAME_LIMIT,
    RESOURCE_NOUN_FIELD,
    RESOURCE_NOUN_LIMIT,
    RULE_LIMIT,
    TONE_FIELD,
    TONE_LIMIT,
    catalog_key_of,
    choice_field,
    faq_answer_field,
    faq_question_field,
    hint_field,
    label_field,
    niche_text_key,
    offer_title_field,
    rule_field,
)


def build_niche_text_catalog(
    template: NicheTemplate, starters: StarterAnswers
) -> NicheTextCatalog:
    """Every editable text of the niche, with the code's own wording."""

    niche: NicheKey = template.key
    fields: list[NicheTextField] = [
        text_field(NAME_FIELD, NicheTextSection.NICHE, template.names, NAME_LIMIT),
        text_field(
            DESCRIPTION_FIELD,
            NicheTextSection.NICHE,
            template.descriptions,
            DESCRIPTION_LIMIT,
        ),
        text_field(
            RESOURCE_NOUN_FIELD,
            NicheTextSection.NICHE,
            template.resource_nouns,
            RESOURCE_NOUN_LIMIT,
        ),
    ]
    questions: list[NicheTextQuestion] = []
    for question in template.questions:
        question_fields, structure = question_texts(niche, question)
        fields.extend(question_fields)
        questions.append(structure)

    fields.extend(rule_fields(niche, HANDOFF_RULES))
    fields.extend(rule_fields(niche, FORBIDDEN_RULES))
    fields.extend(starter_fields(starters))
    return NicheTextCatalog(niche_key=niche, fields=fields, questions=questions)


def question_texts(
    niche: NicheKey, question: QuestionDefinition
) -> tuple[list[NicheTextField], NicheTextQuestion]:
    """A question's editable texts and its structure for the preview."""

    key: QuestionKey = question.key
    fields: list[NicheTextField] = [
        text_field(
            label_field(key),
            NicheTextSection.QUESTION,
            question.labels,
            LABEL_LIMIT,
            key,
        )
    ]
    if question.hints is not None:
        fields.append(
            text_field(
                hint_field(key),
                NicheTextSection.QUESTION,
                question.hints,
                HINT_LIMIT,
                key,
            )
        )

    choices: list[NicheTextChoice] = []
    for choice in question.choices:
        field_key: NicheTextFieldKey = choice_field(key, choice.key)
        if not has_owner_text(catalog_key_of(niche, field_key)):
            choices.append(NicheTextChoice(key=choice.key, fixed_labels=choice.labels))
            continue

        fields.append(
            text_field(
                field_key, NicheTextSection.QUESTION, choice.labels, CHOICE_LIMIT, key
            )
        )
        choices.append(NicheTextChoice(key=choice.key, field_key=field_key))

    return fields, NicheTextQuestion(
        key=key,
        step=question.step,
        answer_type=question.answer_type,
        is_required=question.is_required,
        label_field=label_field(key),
        hint_field=hint_field(key) if question.hints is not None else None,
        choices=choices,
    )


def rule_fields(niche: NicheKey, rules: str) -> list[NicheTextField]:
    """The niche's own handoff or forbidden rules, one field per line."""

    keys = numbered_keys(niche_text_key(niche, rules), OWNER_TEXT_CATALOG)
    return [
        text_field(
            rule_field(rules, position),
            NicheTextSection.RULES,
            owner_text(str(key)),
            RULE_LIMIT,
        )
        for position, key in enumerate(keys, start=1)
    ]


def starter_fields(starters: StarterAnswers) -> list[NicheTextField]:
    """The starter answers' texts a new owner is offered."""

    section: NicheTextSection = NicheTextSection.STARTERS
    fields: list[NicheTextField] = [
        text_field(TONE_FIELD, section, starters.tones, TONE_LIMIT)
    ]
    if starters.booking is not None:
        fields.append(
            text_field(
                CANCELLATION_POLICY_FIELD,
                section,
                starters.booking.cancellation_policies,
                CANCELLATION_POLICY_LIMIT,
            )
        )
    if starters.resource is not None:
        fields.append(
            text_field(
                RESOURCE_NAME_FIELD,
                section,
                starters.resource.names,
                RESOURCE_NAME_LIMIT,
            )
        )
    for faq in starters.faq:
        fields.append(
            text_field(
                faq_question_field(faq.key), section, faq.questions, FAQ_QUESTION_LIMIT
            )
        )
        if faq.answers is not None:
            fields.append(
                text_field(
                    faq_answer_field(faq.key), section, faq.answers, FAQ_ANSWER_LIMIT
                )
            )
    fields.extend(
        text_field(
            offer_title_field(offer.key), section, offer.titles, OFFER_TITLE_LIMIT
        )
        for offer in starters.offers
    )
    return fields


def text_field(
    field_key: NicheTextFieldKey,
    section: NicheTextSection,
    code_texts: LocalizedText,
    max_length: NicheTextLengthLimit,
    question_key: QuestionKey | None = None,
) -> NicheTextField:
    return NicheTextField(
        field_key=field_key,
        section=section,
        question_key=question_key,
        code_texts=code_texts,
        max_length=max_length,
    )

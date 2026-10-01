"""Niche templates rendered in one language for owners."""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.dto.niches import NicheTemplate, QuestionDefinition
from app.schemas.dto.profiles import (
    LocalizedChoiceView,
    LocalizedQuestionView,
    NicheSummaryView,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import ForbiddenRuleText, HandoffRuleText
from app.utilities.knowledge.localized_texts import split_rule_lines


def to_niche_summary(
    template: NicheTemplate,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> NicheSummaryView:
    """What a niche is and what it books, in `language`."""

    return NicheSummaryView(
        key=template.key,
        wave=template.wave,
        name=resolver.resolve(template.names, language),
        description=resolver.resolve(template.descriptions, language),
        recommended_plans=list(template.recommended_plans),
        resource_kind=template.resource_kind,
        booking_unit=template.booking_unit,
        takes_bookings=template.takes_bookings,
        resource_noun=resolver.resolve(template.resource_nouns, language),
        requires_legal_review=template.requires_legal_review,
        integrations=list(template.integrations),
    )


def to_localized_question(
    question: QuestionDefinition,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> LocalizedQuestionView:
    """A niche question with its label, hint and choices in `language`."""

    return LocalizedQuestionView(
        key=question.key,
        fact_key=question.fact_key,
        step=question.step,
        answer_type=question.answer_type,
        is_required=question.is_required,
        label=resolver.resolve(question.labels, language),
        hint=(
            None
            if question.hints is None
            else resolver.resolve(question.hints, language)
        ),
        choices=[
            LocalizedChoiceView(
                key=choice.key,
                label=resolver.resolve(choice.labels, language),
            )
            for choice in question.choices
        ],
    )


def default_handoff_rules(
    template: NicheTemplate,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> list[HandoffRuleText]:
    """The niche's default handoff rules, one per line, in `language`."""

    return [
        HandoffRuleText(line)
        for line in split_rule_lines(
            resolver.resolve(template.default_handoff_rules, language)
        )
    ]


def default_forbidden_rules(
    template: NicheTemplate,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> list[ForbiddenRuleText]:
    """The niche's default forbidden rules, one per line, in `language`."""

    return [
        ForbiddenRuleText(line)
        for line in split_rule_lines(
            resolver.resolve(template.default_forbidden_rules, language)
        )
    ]

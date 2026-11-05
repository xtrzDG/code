"""The profile sections starter answers fill, validated like the owner's own input."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.setup import StarterSection
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessProfileDocument,
    OpeningInterval,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import (
    ForbiddenRuleText,
    HandoffRuleText,
    ToneText,
)
from app.utilities.knowledge.niche_views import (
    default_forbidden_rules,
    default_handoff_rules,
)
from app.utilities.knowledge.opening_hours import validate_opening_intervals
from app.utilities.knowledge.profile_sections import (
    build_booking_rules,
    check_rules,
    check_tone,
)
from app.utilities.setup.starter_views import booking_rules_input, tone

PROFILE_SECTIONS: frozenset[StarterSection] = frozenset(
    {
        StarterSection.HOURS,
        StarterSection.BOOKING_RULES,
        StarterSection.HANDOFF_RULES,
        StarterSection.FORBIDDEN_RULES,
        StarterSection.TONE,
    }
)


@dataclass(frozen=True)
class StarterProfileValues:
    """The values starter answers would give the profile's sections."""

    hours: list[OpeningInterval]
    booking_rules: BookingRules | None
    handoff_rules: list[HandoffRuleText]
    forbidden: list[ForbiddenRuleText]
    tone: ToneText | None


def build_starter_profile_values(
    business: BusinessDocument,
    template: NicheTemplate,
    starters: StarterAnswers,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> StarterProfileValues:
    """
    Every suggested section in `language`, checked by the same rules as a
    wizard step (hours without overlaps, booking rules of the niche).
    """

    return StarterProfileValues(
        hours=validate_opening_intervals(starters.hours, subject="Opening hours"),
        booking_rules=build_booking_rules(
            booking_rules_input(template, starters, language, resolver),
            template,
            business,
        ),
        handoff_rules=check_rules(
            default_handoff_rules(template, language, resolver), subject="handoff"
        ),
        forbidden=check_rules(
            default_forbidden_rules(template, language, resolver), subject="forbidden"
        ),
        tone=check_tone(tone(starters, language, resolver)),
    )


def fill_empty_sections(
    profile: BusinessProfileDocument,
    sections: Sequence[StarterSection],
    values: StarterProfileValues,
) -> list[StarterSection]:
    """Fill the empty ones of `sections` in place; return those filled."""

    filled: list[StarterSection] = []
    for section in sections:
        match section:
            case StarterSection.HOURS if profile.hours == [] and values.hours:
                profile.hours = list(values.hours)
            case StarterSection.BOOKING_RULES if (
                profile.booking_rules is None and values.booking_rules is not None
            ):
                profile.booking_rules = values.booking_rules.model_copy()
            case StarterSection.HANDOFF_RULES if (
                profile.handoff_rules == [] and values.handoff_rules
            ):
                profile.handoff_rules = list(values.handoff_rules)
            case StarterSection.FORBIDDEN_RULES if (
                profile.forbidden == [] and values.forbidden
            ):
                profile.forbidden = list(values.forbidden)
            case StarterSection.TONE if profile.tone is None and values.tone:
                profile.tone = values.tone
            case _:
                continue

        filled.append(section)

    return filled

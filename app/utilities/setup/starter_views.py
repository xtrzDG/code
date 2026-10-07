"""
Starter answers in one language: what they suggest, which profile sections
are still empty, and the inputs that applying them saves.
"""

from collections.abc import Sequence

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.setup import StarterSection, StarterSectionState
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemUpsertInput
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles.business_profile import BookingRulesInput
from app.schemas.dto.resources import ResourceInput
from app.schemas.dto.setup.starter_answers import (
    StarterFaqView,
    StarterOfferView,
    StarterResourceView,
    StarterSectionView,
)
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import CancellationPolicyText, ToneText
from app.schemas.typings.setup.constrained_strings import StarterEntryKey
from app.utilities.knowledge.search_text import fold_words


def offered_sections(
    template: NicheTemplate,
    starters: StarterAnswers,
) -> list[StarterSection]:
    """The sections a niche suggests (booking ones only for booking niches)."""

    takes_bookings: bool = bool(template.takes_bookings)
    sections: list[StarterSection] = [StarterSection.HOURS]
    if takes_bookings and starters.booking is not None:
        sections.append(StarterSection.BOOKING_RULES)

    if takes_bookings and starters.resource is not None:
        sections.append(StarterSection.RESOURCE)

    sections.extend(
        [
            StarterSection.HANDOFF_RULES,
            StarterSection.FORBIDDEN_RULES,
            StarterSection.TONE,
            StarterSection.FAQ,
        ]
    )
    return sections


def is_section_filled(
    section: StarterSection,
    profile: BusinessProfileDocument | None,
    resources: Sequence[ResourceDocument],
    missing_faq: Sequence[KnowledgeItemUpsertInput],
) -> bool:
    """Whether the owner already has the section (applying then keeps it)."""

    match section:
        case StarterSection.HOURS:
            return profile is not None and profile.hours != []
        case StarterSection.BOOKING_RULES:
            return profile is not None and profile.booking_rules is not None
        case StarterSection.RESOURCE:
            return resources != []
        case StarterSection.HANDOFF_RULES:
            return profile is not None and profile.handoff_rules != []
        case StarterSection.FORBIDDEN_RULES:
            return profile is not None and profile.forbidden != []
        case StarterSection.TONE:
            return profile is not None and profile.tone is not None
        case StarterSection.FAQ:
            return missing_faq == []


def section_views(
    sections: Sequence[StarterSection],
    profile: BusinessProfileDocument | None,
    resources: Sequence[ResourceDocument],
    missing_faq: Sequence[KnowledgeItemUpsertInput],
) -> list[StarterSectionView]:
    return [
        StarterSectionView(
            section=section,
            state=(
                StarterSectionState.ALREADY_SET
                if is_section_filled(section, profile, resources, missing_faq)
                else StarterSectionState.SUGGESTED
            ),
        )
        for section in sections
    ]


def booking_rules_input(
    template: NicheTemplate,
    starters: StarterAnswers,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> BookingRulesInput | None:
    """The suggested booking rules, ready for the booking rules step."""

    if not template.takes_bookings or starters.booking is None:
        return None

    return BookingRulesInput(
        resource_kind=template.resource_kind,
        slot_minutes=starters.booking.slot_minutes,
        max_party_size=starters.booking.max_party_size,
        min_notice_minutes=starters.booking.min_notice_minutes,
        cancellation_policy=CancellationPolicyText(
            resolver.resolve(starters.booking.cancellation_policies, language)
        ),
    )


def resource_input(
    template: NicheTemplate,
    starters: StarterAnswers,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> ResourceInput | None:
    """The suggested first resource (niche kind and booking unit)."""

    if not template.takes_bookings or starters.resource is None:
        return None

    return ResourceInput(
        kind=template.resource_kind,
        name=ResourceName(resolver.resolve(starters.resource.names, language)),
        capacity=starters.resource.capacity,
        unit_count=starters.resource.unit_count,
        booking_unit=template.booking_unit,
    )


def resource_view(
    template: NicheTemplate,
    resource: ResourceInput | None,
) -> StarterResourceView | None:
    if resource is None:
        return None

    return StarterResourceView(
        kind=resource.kind or template.resource_kind,
        booking_unit=resource.booking_unit or template.booking_unit,
        name=resource.name,
        capacity=resource.capacity,
        unit_count=resource.unit_count,
        slot_minutes=resource.slot_minutes,
    )


def tone(
    starters: StarterAnswers,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> ToneText:
    return ToneText(resolver.resolve(starters.tones, language))


def faq_views(
    starters: StarterAnswers,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> list[StarterFaqView]:
    return [
        StarterFaqView(
            key=entry.key,
            question=KnowledgeTitle(resolver.resolve(entry.questions, language)),
            answer=(
                None
                if entry.answers is None
                else KnowledgeBody(resolver.resolve(entry.answers, language))
            ),
            is_ready=entry.answers is not None,
        )
        for entry in starters.faq
    ]


def offer_views(
    starters: StarterAnswers,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> list[StarterOfferView]:
    return [
        StarterOfferView(
            key=offer.key,
            kind=offer.kind,
            title=KnowledgeTitle(resolver.resolve(offer.titles, language)),
            duration_minutes=offer.duration_minutes,
        )
        for offer in starters.offers
    ]


def missing_faq_inputs(
    faq: Sequence[StarterFaqView],
    existing_items: Sequence[KnowledgeItemDocument],
    language: LanguageTag,
    keys: Sequence[StarterEntryKey] | None = None,
) -> list[KnowledgeItemUpsertInput]:
    """
    New FAQ items for the ready questions (those `keys` name, or all) the
    business has not got yet: a question already in its knowledge base is
    never touched, so an answer the owner edited stays theirs.
    """

    present: set[str] = {
        fold_words(item.title)
        for item in existing_items
        if item.kind is KnowledgeItemKind.FAQ
    }
    return [
        KnowledgeItemUpsertInput(
            kind=KnowledgeItemKind.FAQ,
            title=entry.question,
            body=entry.answer,
            languages=[language],
        )
        for entry in faq
        if entry.answer is not None
        and (keys is None or entry.key in keys)
        and fold_words(entry.question) not in present
    ]

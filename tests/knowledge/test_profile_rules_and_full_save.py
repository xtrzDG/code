"""Rules, tone, FAQ and channel steps, the full profile save and blank texts."""

import pytest

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.profiles import BusinessAddress, BusinessLink
from app.schemas.dto.profiles.business_profile import (
    BookingRulesInput,
    BusinessProfileQuery,
    ContactsInput,
    FaqEntryInput,
    ProfileInput,
    SaveProfileCommand,
)
from app.schemas.dto.profiles.profile_steps import (
    BookingRulesStepInput,
    ChannelsStepInput,
    ContactsAndHoursStepInput,
    FaqAndHandoffStepInput,
    NicheAndLanguagesStepInput,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    PartySize,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ForbiddenRuleText,
    HandoffRuleText,
    ToneText,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.wizard_helpers import answer, choices, hours, save_step


def test_faq_and_handoff_step_saves_rules_tone_and_faq_items() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    result = save_step(
        harness,
        business.id,
        FaqAndHandoffStepInput(
            faq=[
                FaqEntryInput(
                    question=KnowledgeTitle("Есть ли парковка?"),
                    answer=KnowledgeBody("Да, бесплатная, во дворе"),
                    languages=[LanguageTag("ru")],
                )
            ],
            handoff_rules=[
                HandoffRuleText(" Жалоба "),
                HandoffRuleText("жалоба"),
                HandoffRuleText(""),
                HandoffRuleText("Банкет больше 20 человек"),
            ],
            forbidden=[ForbiddenRuleText("Скидки без согласования")],
            tone=ToneText("  дружелюбно и коротко "),
        ),
    )

    assert result.profile.handoff_rules == [" Жалоба ", "Банкет больше 20 человек"]
    assert result.profile.forbidden == ["Скидки без согласования"]
    assert result.profile.tone == "  дружелюбно и коротко "
    assert result.saved_knowledge_items[0].kind is KnowledgeItemKind.FAQ
    assert result.saved_knowledge_items[0].title == "Есть ли парковка?"


def test_too_long_rules_and_tone_are_rejected() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="handoff"):
        save_step(
            harness,
            business.id,
            FaqAndHandoffStepInput(handoff_rules=[HandoffRuleText("x" * 301)]),
        )

    with pytest.raises(ValidationFailedError, match="tone"):
        save_step(
            harness,
            business.id,
            FaqAndHandoffStepInput(tone=ToneText("x" * 201)),
        )


def test_channels_step_keeps_one_link_per_kind() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    menu = BusinessLink(
        kind=BusinessLinkKind.MENU, url=WebLink("https://example.ge/menu")
    )

    result = save_step(
        harness,
        business.id,
        ChannelsStepInput(links=[menu], is_recording_notice_enabled=False),
    )

    assert result.profile.links == [menu]
    assert result.profile.is_recording_notice_enabled is False
    with pytest.raises(ValidationFailedError, match="two menu links"):
        save_step(harness, business.id, ChannelsStepInput(links=[menu, menu]))


def test_full_profile_save_replaces_everything_and_validates_like_steps() -> None:
    harness = KnowledgeHarness()
    owner_id = UserId()
    business = harness.add_business(niche_key=NicheKey.BEAUTY_SALON, owner_id=owner_id)
    save_step(
        harness,
        business.id,
        ChannelsStepInput(
            links=[
                BusinessLink(
                    kind=BusinessLinkKind.BOOKING_PAGE,
                    url=WebLink("https://salon.example/book"),
                )
            ]
        ),
    )

    view = harness.save_profile.run(
        SaveProfileCommand(
            business_id=business.id,
            actor_id=owner_id,
            profile=ProfileInput(
                address=BusinessAddress(text=AddressText("Batumi, Gorgiladze 10")),
                hours=[hours(Weekday.SATURDAY, 600, 1200)],
                contacts=ContactsInput(
                    handoff_phone_number=RawPhoneNumberInput("+995 577 11 22 33")
                ),
                booking_rules=BookingRulesInput(max_party_size=PartySize(1)),
                answers=[
                    choices("service_categories", "nails", "hair"),
                    answer("break_between_appointments", "15"),
                ],
            ),
        )
    )

    assert view.links == []
    assert view.booking_rules is not None
    assert view.booking_rules.resource_kind is ResourceKind.STAFF
    assert view.booking_rules.slot_minutes == 60
    assert [item.answer for item in view.niche_answers] == ["hair,nails", "15"]
    assert view.contacts.handoff_phone_number == "+995577112233"
    assert len(harness.audit_log_repo.list_by_business(business.id)) == 1

    with pytest.raises(ValidationFailedError, match="does not exist"):
        harness.save_profile.run(
            SaveProfileCommand(
                business_id=business.id,
                actor_id=owner_id,
                profile=ProfileInput(answers=[answer("cuisine", "Georgian")]),
            )
        )


def test_profile_of_unknown_business_is_not_found() -> None:
    harness = KnowledgeHarness()

    with pytest.raises(NotFoundError):
        harness.get_business_profile.run(BusinessProfileQuery(business_id=BusinessId()))

    with pytest.raises(NotFoundError):
        save_step(harness, BusinessId(), NicheAndLanguagesStepInput())


def test_blank_texts_are_rejected_or_cleared() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="address is empty"):
        save_step(
            harness,
            business.id,
            ContactsAndHoursStepInput(address=BusinessAddress(text=AddressText("  "))),
        )

    result = save_step(
        harness,
        business.id,
        FaqAndHandoffStepInput(
            tone=ToneText("   "),
            forbidden=[ForbiddenRuleText(" "), ForbiddenRuleText("No discounts")],
        ),
    )
    rules = save_step(
        harness,
        business.id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(
                max_party_size=PartySize(2),
                cancellation_policy=CancellationPolicyText(" "),
            )
        ),
    )

    assert result.profile.tone is None
    assert result.profile.forbidden == ["No discounts"]
    assert rules.profile.booking_rules is not None
    assert rules.profile.booking_rules.cancellation_policy is None

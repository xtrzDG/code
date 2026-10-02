"""Saving wizard steps: partial progress, phones, hours and audited contact changes."""

import pytest

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.domain.profiles import BusinessAddress
from app.schemas.dto.profiles.business_profile import (
    BusinessProfileQuery,
    ContactsInput,
)
from app.schemas.dto.profiles.profile_steps import (
    ContactsAndHoursStepInput,
    NicheAndLanguagesStepInput,
)
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.wizard_helpers import answer, hours, save_step


def test_steps_store_partial_progress_and_keep_other_steps() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    first = save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(
            answers_language=LanguageTag("ru"),
            answers=[answer("cuisine", "  Грузинская  ")],
        ),
    )
    second = save_step(
        harness,
        business.id,
        ContactsAndHoursStepInput(
            address=BusinessAddress(
                text=AddressText(" Тбилиси, ул. Руставели 1 "),
                maps_url=WebLink("https://maps.example.com/venue"),
            ),
            hours=[hours(Weekday.MONDAY, 720, 1380), hours(Weekday.FRIDAY, 1080, 1440)],
            contacts=ContactsInput(
                public_phone_number=RawPhoneNumberInput("555 12 34 56"),
                handoff_phone_number=RawPhoneNumberInput("+995 599 12 34 56"),
            ),
        ),
    )

    assert first.step is ProfileWizardStep.NICHE_AND_LANGUAGES
    assert first.profile.is_saved is True
    assert second.profile.answers_language == "ru"
    assert [item.answer for item in second.profile.niche_answers] == ["Грузинская"]
    assert second.profile.address is not None
    assert second.profile.address.text == " Тбилиси, ул. Руставели 1 "
    assert second.profile.contacts.public_phone_number == "+995555123456"
    assert second.profile.contacts.handoff_phone_number == "+995599123456"
    assert harness.phone_number_parser.country_hints == ["GE", "GE"]
    stored = harness.get_business_profile.run(
        BusinessProfileQuery(business_id=business.id)
    )
    assert len(stored.hours) == 2
    assert stored.updated_at == harness.wall_clock.now_unix()


@pytest.mark.parametrize(
    ("country_code", "currency_code", "timezone", "raw_phone", "expected_e164"),
    [
        ("DE", "EUR", "Europe/Berlin", "030 1234567", "+49301234567"),
        ("IL", "ILS", "Asia/Jerusalem", "050-234-5678", "+972502345678"),
        ("JP", "JPY", "Asia/Tokyo", "090-1234-5678", "+819012345678"),
        ("BR", "BRL", "America/Sao_Paulo", "(11) 91234-5678", "+5511912345678"),
        ("GE", "GEL", "Asia/Tbilisi", "+1 212 555 0100", "+12125550100"),
    ],
)
def test_phones_of_any_country_are_stored_in_e164(
    country_code: str,
    currency_code: str,
    timezone: str,
    raw_phone: str,
    expected_e164: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        country_code=country_code,
        currency_code=currency_code,
        timezone=timezone,
        languages=("en",),
        owner_language="en",
    )

    result = save_step(
        harness,
        business.id,
        ContactsAndHoursStepInput(
            contacts=ContactsInput(handoff_phone_number=RawPhoneNumberInput(raw_phone))
        ),
    )

    assert result.profile.contacts.handoff_phone_number == expected_e164


def test_invalid_phone_rejects_the_whole_step() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(InvalidPhoneNumberError):
        save_step(
            harness,
            business.id,
            ContactsAndHoursStepInput(
                hours=[hours(Weekday.MONDAY, 600, 1200)],
                contacts=ContactsInput(
                    public_phone_number=RawPhoneNumberInput("12"),
                ),
            ),
        )

    assert harness.business_profile_repo.get_by_business(business.id) is None


def test_hours_validation_errors_reach_the_owner() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="overlap"):
        save_step(
            harness,
            business.id,
            ContactsAndHoursStepInput(
                hours=[
                    hours(Weekday.MONDAY, 600, 900),
                    hours(Weekday.MONDAY, 800, 1000),
                ]
            ),
        )


def test_contact_phone_changes_are_audited_but_other_saves_are_not() -> None:
    harness = KnowledgeHarness()
    owner_id = UserId()
    business = harness.add_business(owner_id=owner_id)
    contacts = ContactsAndHoursStepInput(
        contacts=ContactsInput(handoff_phone_number=RawPhoneNumberInput("599123456"))
    )

    save_step(harness, business.id, contacts, actor_id=owner_id)
    save_step(harness, business.id, contacts, actor_id=owner_id)
    save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(answers=[answer("cuisine", "Georgian")]),
        actor_id=owner_id,
    )

    entries = harness.audit_log_repo.list_by_business(business.id)
    assert [entry.action for entry in entries] == [AuditAction.UPDATE]
    assert entries[0].actor_id == owner_id
    assert entries[0].entity == "business_profile.contacts"

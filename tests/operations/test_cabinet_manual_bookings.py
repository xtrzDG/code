"""Manual bookings from the cabinet: phones, limits, input and refusal reasons."""

from datetime import datetime

import pytest

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.profiles import BookingRules
from app.schemas.exceptions.application_errors import (
    ConflictError,
    InvalidPhoneNumberError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.constrained_integers import (
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.utilities.scheduling.resource_selection import ensure_party_size_allowed
from tests.operations.cabinet_bookings_helpers import Cabinet


def test_manual_booking_parses_a_national_phone_and_creates_the_contact() -> None:
    cabinet = Cabinet()

    result = cabinet.world.create_manual_booking().run(cabinet.manual())

    assert result.booking.contact_phone_number == "+995555123456"
    assert result.booking.contact_id == cabinet.customer.id
    assert result.booking.contact_name == "Levan"
    assert "დადასტურებულია" in str(result.confirmation_text)
    actions = [
        (entry.action, str(entry.entity))
        for entry in cabinet.world.audit_repo.list_by_business(cabinet.business.id)
    ]
    assert actions == [(AuditAction.UPDATE, "contact"), (AuditAction.CREATE, "booking")]
    assert len(cabinet.world.calendar_sync.synced) == 1
    assert cabinet.world.notifier.sent == []


@pytest.mark.parametrize(
    ("country_code", "timezone", "raw_phone", "expected"),
    [
        ("IT", "Europe/Rome", "333 123 4567", "+393331234567"),
        ("US", "America/New_York", "(650) 253-0000", "+16502530000"),
        ("IN", "Asia/Kolkata", "098765 43210", "+919876543210"),
        ("NZ", "Pacific/Auckland", "+64 21 123 4567", "+64211234567"),
    ],
)
def test_manual_booking_accepts_phones_of_any_country(
    country_code: str,
    timezone: str,
    raw_phone: str,
    expected: str,
) -> None:
    cabinet = Cabinet(country_code, timezone, ("en",))

    result = cabinet.world.create_manual_booking().run(
        cabinet.manual(name="Alex", phone=raw_phone)
    )

    assert result.booking.contact_phone_number == expected
    actions = [
        (entry.action, str(entry.entity))
        for entry in cabinet.world.audit_repo.list_by_business(cabinet.business.id)
    ]
    assert actions == [(AuditAction.CREATE, "contact"), (AuditAction.CREATE, "booking")]


def test_manual_booking_skips_online_limits_but_not_hours_or_capacity() -> None:
    cabinet = Cabinet()
    use_case = cabinet.world.create_manual_booking()

    big_party = use_case.run(cabinet.manual(party_size=30, phone=None))
    walk_in = use_case.run(cabinet.manual(day="2026-10-05", time="12:15", phone=None))

    assert big_party.booking.resource_name == "Banquet hall"
    assert walk_in.booking.time == "12:15"
    with pytest.raises(ValidationFailedError, match="closed"):
        use_case.run(cabinet.manual(day="2026-10-05", time="11:30", phone=None))

    cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-05T13:00:00+04:00"))
    with pytest.raises(ValidationFailedError, match="too soon"):
        use_case.run(cabinet.manual(day="2026-10-05", time="12:30", phone=None))

    with pytest.raises(ConflictError):
        use_case.run(cabinet.manual(party_size=30, phone=None))

    with pytest.raises(InvalidPhoneNumberError):
        use_case.run(cabinet.manual(phone="12"))


def test_manual_booking_confirmation_uses_the_requested_language() -> None:
    cabinet = Cabinet()

    result = cabinet.world.create_manual_booking().run(cabinet.manual(language="uk"))

    assert str(result.confirmation_text).startswith("Ваше бронювання в «Salobie Bia»")


class TestManualBookingInput:
    def test_country_hint_reads_a_national_number_of_another_country(self) -> None:
        cabinet = Cabinet()

        result = cabinet.world.create_manual_booking().run(
            cabinet.manual(phone="333 123 4567", country_hint="IT")
        )

        assert result.booking.contact_phone_number == "+393331234567"

    def test_booking_from_a_conversation_is_linked_to_its_customer(self) -> None:
        cabinet = Cabinet()
        customer = cabinet.world.add_contact(cabinet.business, "Nino", language="en")
        conversation = cabinet.world.add_conversation(
            cabinet.business, customer, channel=ChannelKind.TELEGRAM
        )

        result = cabinet.world.create_manual_booking().run(
            cabinet.manual(
                name="Nino B.", phone="599 11 22 33", conversation_id=conversation.id
            )
        )

        booking = result.booking
        assert booking.conversation_id == conversation.id
        assert booking.contact_id == customer.id
        assert booking.contact_name == "Nino B."
        assert booking.contact_phone_number == "+995599112233"
        assert booking.source_channel is ChannelKind.TELEGRAM
        assert booking.language == "en"
        assert str(result.confirmation_text).startswith("Your booking")

    def test_unknown_conversation_is_not_found(self) -> None:
        cabinet = Cabinet()

        with pytest.raises(NotFoundError):
            cabinet.world.create_manual_booking().run(
                cabinet.manual(conversation_id=ConversationId())
            )


def refusal(error: pytest.ExceptionInfo[Exception]) -> tuple[str, list[str]]:
    assert isinstance(error.value, ApplicationError)
    [reason] = error.value.reasons
    return str(reason.code), [str(detail) for detail in reason.details]


def test_booking_refusals_carry_reason_codes_for_the_cabinet() -> None:
    cabinet = Cabinet()
    use_case = cabinet.world.create_manual_booking()

    with pytest.raises(ValidationFailedError) as closed:
        use_case.run(cabinet.manual(day="2026-10-05", time="11:30", phone=None))
    with pytest.raises(ValidationFailedError) as no_seat:
        use_case.run(cabinet.manual(party_size=500, phone=None))
    use_case.run(cabinet.manual(party_size=30, phone=None))
    with pytest.raises(ConflictError) as taken:
        use_case.run(cabinet.manual(party_size=30, phone=None))
    cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-05T13:00:00+04:00"))
    with pytest.raises(ValidationFailedError) as too_soon:
        use_case.run(cabinet.manual(day="2026-10-05", time="12:30", phone=None))

    assert refusal(closed) == ("closed", ["2026-10-05"])
    assert refusal(no_seat) == ("no_seating_resource", ["500"])
    assert refusal(taken) == ("taken", ["2026-10-06"])
    assert refusal(too_soon) == ("too_soon", [])


def test_the_online_party_limit_names_the_maximum_in_its_reason() -> None:
    rules = BookingRules(
        resource_kind=ResourceKind.TABLE,
        slot_minutes=SlotDurationMinutes(30),
        max_party_size=PartySize(8),
    )

    with pytest.raises(ValidationFailedError) as too_large:
        ensure_party_size_allowed(PartySize(12), rules)

    assert refusal(too_large) == ("party_too_large", ["8"])

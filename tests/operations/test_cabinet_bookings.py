from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.bookings import AvailabilityQuery, BookingView
from app.schemas.dto.operations import (
    ListBookingsQuery,
    ManualBookingCommand,
    UpdateBookingStatusCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    InvalidPhoneNumberError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.builders import OperationsWorld


class Cabinet:
    def __init__(
        self,
        country_code: str = "GE",
        timezone: str = "Asia/Tbilisi",
        languages: tuple[str, ...] = ("ka", "ru", "en"),
    ) -> None:
        self.world = OperationsWorld()
        self.staff_id = UserId()
        self.business = self.world.add_business(
            country_code=country_code,
            timezone=timezone,
            languages=languages,
            staff_ids=(self.staff_id,),
        )
        self.world.add_profile(self.business)
        self.table = self.world.add_resource(self.business, "Table 4", capacity=4)
        self.hall = self.world.add_resource(self.business, "Banquet hall", capacity=40)
        self.customer = self.world.add_contact(self.business, "Giorgi", "+995555123456")

    def manual(
        self,
        name: str = "Levan",
        phone: str | None = "555 12 34 56",
        time: str = "19:00",
        day: str = "2026-10-06",
        party_size: int = 4,
        language: str | None = None,
    ) -> ManualBookingCommand:
        return ManualBookingCommand(
            business_id=self.business.id,
            actor_id=self.staff_id,
            contact_name=ContactName(name),
            contact_phone_number=None if phone is None else RawPhoneNumberInput(phone),
            date=LocalDate(day),
            time=LocalTimeOfDay(time),
            party_size=PartySize(party_size),
            source_channel=ChannelKind.PHONE,
            language=None if language is None else LanguageTag(language),
        )

    def list(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        status: BookingStatus | None = None,
        include_sandbox: bool = False,
    ) -> list[str]:
        result = self.world.list_bookings().run(
            ListBookingsQuery(
                business_id=self.business.id,
                actor_id=self.staff_id,
                date_from=None if date_from is None else LocalDate(date_from),
                date_to=None if date_to is None else LocalDate(date_to),
                status=status,
                include_sandbox=include_sandbox,
            )
        )
        return [f"{item.date} {item.time} {item.contact_name}" for item in result.items]


def test_list_filters_by_local_dates_status_and_sandbox_and_is_audited() -> None:
    cabinet = Cabinet()
    # 01:00 local on Oct 6 is still Oct 5 in UTC.
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.table,
        cabinet.customer,
        "2026-10-06T01:00:00+04:00",
        "2026-10-06T02:00:00+04:00",
    )
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.table,
        cabinet.customer,
        "2026-10-07T19:00:00+04:00",
        "2026-10-07T21:00:00+04:00",
        status=BookingStatus.CANCELLED,
    )
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.hall,
        cabinet.customer,
        "2026-10-06T19:00:00+04:00",
        "2026-10-06T21:00:00+04:00",
        is_sandbox=True,
    )

    assert cabinet.list("2026-10-06", "2026-10-06") == ["2026-10-06 01:00 Giorgi"]
    assert cabinet.list(status=BookingStatus.CANCELLED) == ["2026-10-07 19:00 Giorgi"]
    assert len(cabinet.list(include_sandbox=True)) == 3
    entries = cabinet.world.audit_repo.list_by_business(cabinet.business.id)
    assert {(entry.action, entry.entity, entry.actor_id) for entry in entries} == {
        (AuditAction.VIEW, "booking", cabinet.staff_id)
    }
    with pytest.raises(ValidationFailedError):
        cabinet.list("2026-10-07", "2026-10-06")


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


class TestStatusUpdates:
    def update(
        self,
        cabinet: Cabinet,
        booking_id: BookingId,
        status: BookingStatus,
    ) -> BookingView:
        return cabinet.world.update_booking_status().run(
            UpdateBookingStatusCommand(
                business_id=cabinet.business.id,
                actor_id=cabinet.staff_id,
                booking_id=booking_id,
                status=status,
            )
        )

    def test_completion_no_show_and_confirmation(self) -> None:
        cabinet = Cabinet()
        booking = cabinet.world.add_booking(
            cabinet.business,
            cabinet.table,
            cabinet.customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
        )
        pending = cabinet.world.add_booking(
            cabinet.business,
            cabinet.hall,
            cabinet.customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
            status=BookingStatus.PENDING,
        )

        assert self.update(cabinet, booking.id, BookingStatus.NO_SHOW).status is (
            BookingStatus.NO_SHOW
        )
        assert self.update(cabinet, pending.id, BookingStatus.CONFIRMED).status is (
            BookingStatus.CONFIRMED
        )
        assert self.update(cabinet, pending.id, BookingStatus.CONFIRMED).status is (
            BookingStatus.CONFIRMED
        )
        assert len(cabinet.world.calendar_sync.synced) == 2
        audited = [
            entry.action
            for entry in cabinet.world.audit_repo.list_by_business(cabinet.business.id)
        ]
        assert audited == [AuditAction.UPDATE, AuditAction.UPDATE]
        # A no-show frees the table for walk-ins.
        free = cabinet.world.check_availability().run(
            AvailabilityQuery(
                business_id=cabinet.business.id,
                date=LocalDate("2026-10-06"),
                time=LocalTimeOfDay("19:00"),
                party_size=PartySize(4),
            )
        )
        assert any(slot.resource_name == "Table 4" for slot in free.slots)

    def test_forbidden_transitions_and_unknown_booking(self) -> None:
        cabinet = Cabinet()
        booking = cabinet.world.add_booking(
            cabinet.business,
            cabinet.table,
            cabinet.customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
        )
        self.update(cabinet, booking.id, BookingStatus.COMPLETED)

        with pytest.raises(ConflictError):
            self.update(cabinet, booking.id, BookingStatus.CANCELLED)

        with pytest.raises(ConflictError):
            self.update(cabinet, booking.id, BookingStatus.PENDING)

        with pytest.raises(NotFoundError):
            self.update(cabinet, BookingId(), BookingStatus.CANCELLED)


def test_clock_is_the_injected_one() -> None:
    cabinet = Cabinet()
    cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-06T15:30:00+00:00"))

    with pytest.raises(ValidationFailedError, match="too soon"):
        cabinet.world.create_manual_booking().run(cabinet.manual(time="19:00"))

from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingOrder, BookingStatus, BookingUnit
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.bookings import AvailabilityQuery, BookingView
from app.schemas.dto.operations import (
    BookingPage,
    ListBookingsQuery,
    ManualBookingCommand,
    UpdateBookingCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import (
    ConflictError,
    InvalidPhoneNumberError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import NightCount, PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.builders import OperationsWorld, every_day


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
        country_hint: str | None = None,
        conversation_id: ConversationId | None = None,
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
            country_hint=None if country_hint is None else CountryCode(country_hint),
            conversation_id=conversation_id,
        )

    def page(
        self,
        resource_id: ResourceId | None = None,
        order: BookingOrder = BookingOrder.EARLIEST_FIRST,
        size: int = 50,
        cursor: BookingPage | None = None,
    ) -> BookingPage:
        return self.world.list_bookings().run(
            ListBookingsQuery(
                business_id=self.business.id,
                actor_id=self.staff_id,
                resource_id=resource_id,
                order=order,
                page=PageRequest(
                    size=PageSize(size),
                    cursor=None if cursor is None else cursor.next_cursor,
                ),
            )
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
        return cabinet.world.update_booking().run(
            UpdateBookingCommand(
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


def test_list_pages_by_start_time_and_filters_by_resource() -> None:
    cabinet = Cabinet()
    for day in ("2026-10-08", "2026-10-06", "2026-10-07"):
        cabinet.world.add_booking(
            cabinet.business,
            cabinet.table,
            cabinet.customer,
            f"{day}T19:00:00+04:00",
            f"{day}T21:00:00+04:00",
        )
    cabinet.world.add_booking(
        cabinet.business,
        cabinet.hall,
        cabinet.customer,
        "2026-10-06T13:00:00+04:00",
        "2026-10-06T15:00:00+04:00",
    )

    first = cabinet.page(size=2)
    second = cabinet.page(size=2, cursor=first)
    latest = cabinet.page(order=BookingOrder.LATEST_FIRST, size=1)
    tables = cabinet.page(resource_id=cabinet.table.id)

    assert [(item.date, item.time) for item in first.items] == [
        ("2026-10-06", "13:00"),
        ("2026-10-06", "19:00"),
    ]
    assert first.next_cursor is not None
    assert [item.date for item in second.items] == ["2026-10-07", "2026-10-08"]
    assert second.next_cursor is None
    assert [item.date for item in latest.items] == ["2026-10-08"]
    assert {item.resource_name for item in tables.items} == {"Table 4"}
    assert len(tables.items) == 3


def test_booking_view_carries_creation_reminder_and_language() -> None:
    cabinet = Cabinet()
    conversation = cabinet.world.add_conversation(cabinet.business, cabinet.customer)

    result = cabinet.world.create_manual_booking().run(
        cabinet.manual(phone=None, language="ru", conversation_id=conversation.id)
    )
    listed = cabinet.page().items[0]

    assert listed.id == result.booking.id
    assert listed.language == "ru"
    assert listed.reminder_sent_at is None
    assert listed.created_at == cabinet.world.clock.now_microseconds()
    assert listed.conversation_id == conversation.id


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


class TestBookingDetails:
    def booking(self, cabinet: Cabinet, party_size: int = 2) -> BookingView:
        return (
            cabinet.world.create_manual_booking()
            .run(cabinet.manual(phone=None, party_size=party_size))
            .booking
        )

    def update(
        self,
        cabinet: Cabinet,
        booking_id: BookingId,
        party_size: int | None = None,
        resource_id: ResourceId | None = None,
        notes: str | None = None,
        contact_name: str | None = None,
    ) -> BookingView:
        return cabinet.world.update_booking().run(
            UpdateBookingCommand(
                business_id=cabinet.business.id,
                actor_id=cabinet.staff_id,
                booking_id=booking_id,
                party_size=None if party_size is None else PartySize(party_size),
                resource_id=resource_id,
                notes=None if notes is None else BookingNote(notes),
                contact_name=None
                if contact_name is None
                else ContactName(contact_name),
            )
        )

    def test_party_size_notes_and_name_change_and_are_audited(self) -> None:
        cabinet = Cabinet()
        booking = self.booking(cabinet)

        changed = self.update(
            cabinet,
            booking.id,
            party_size=3,
            notes="High chair",
            contact_name="Levan K.",
        )
        cleared = self.update(cabinet, booking.id, notes="   ")

        assert changed.party_size == 3
        assert changed.notes == "High chair"
        assert changed.contact_name == "Levan K."
        assert (changed.date, changed.time) == (booking.date, booking.time)
        assert cleared.notes is None
        audited = [
            (entry.action, str(entry.entity))
            for entry in cabinet.world.audit_repo.list_by_business(cabinet.business.id)
        ][2:]
        assert audited == [
            (AuditAction.UPDATE, "booking"),
            (AuditAction.UPDATE, "contact"),
            (AuditAction.UPDATE, "booking"),
        ]
        assert len(cabinet.world.calendar_sync.synced) == 3

    def test_party_size_must_fit_the_resource(self) -> None:
        cabinet = Cabinet()
        booking = self.booking(cabinet)

        with pytest.raises(ValidationFailedError, match="seats at most 4"):
            self.update(cabinet, booking.id, party_size=6)

        moved = self.update(
            cabinet, booking.id, party_size=6, resource_id=cabinet.hall.id
        )
        assert (moved.resource_name, moved.party_size) == ("Banquet hall", 6)

    def test_resource_change_needs_a_free_open_unit_at_the_booked_time(self) -> None:
        cabinet = Cabinet()
        booking = self.booking(cabinet)
        cabinet.world.add_booking(
            cabinet.business,
            cabinet.hall,
            cabinet.customer,
            "2026-10-06T18:00:00+04:00",
            "2026-10-06T20:00:00+04:00",
        )
        terrace = cabinet.world.add_resource(
            cabinet.business,
            "Terrace",
            capacity=6,
            schedule=every_day_until("18:00"),
        )
        inactive = cabinet.world.add_resource(
            cabinet.business, "Old table", is_active=False
        )

        with pytest.raises(ConflictError):
            self.update(cabinet, booking.id, resource_id=cabinet.hall.id)
        with pytest.raises(ValidationFailedError, match="closed"):
            self.update(cabinet, booking.id, resource_id=terrace.id)
        with pytest.raises(NotFoundError):
            self.update(cabinet, booking.id, resource_id=inactive.id)

    def test_resource_must_be_booked_the_same_way(self) -> None:
        cabinet = Cabinet()
        booking = self.booking(cabinet)
        room = cabinet.world.add_resource(
            cabinet.business, "Room 1", booking_unit=BookingUnit.NIGHT
        )

        with pytest.raises(ValidationFailedError, match="nights"):
            self.update(cabinet, booking.id, resource_id=room.id)

    def test_finished_booking_keeps_its_place_but_takes_notes(self) -> None:
        cabinet = Cabinet()
        booking = self.booking(cabinet)
        TestStatusUpdates().update(cabinet, booking.id, BookingStatus.COMPLETED)

        with pytest.raises(ConflictError):
            self.update(cabinet, booking.id, party_size=3)

        assert self.update(cabinet, booking.id, notes="Paid cash").notes == "Paid cash"

    def test_empty_name_is_refused(self) -> None:
        cabinet = Cabinet()
        booking = self.booking(cabinet)

        with pytest.raises(ValidationFailedError, match="name"):
            self.update(cabinet, booking.id, contact_name="  ")


class TestFullDayAvailability:
    def query(self, cabinet: Cabinet, party_size: int, full_day: bool) -> list[str]:
        result = cabinet.world.check_availability().run(
            AvailabilityQuery(
                business_id=cabinet.business.id,
                date=LocalDate("2026-10-05"),
                party_size=PartySize(party_size),
                full_day=full_day,
            )
        )
        return [f"{slot.time} {slot.resource_name}" for slot in result.slots]

    def test_lists_every_slot_of_every_resource_from_now(self) -> None:
        cabinet = Cabinet()
        # 12:00 local; the profile asks for 60 minutes of notice online.
        cabinet.world.clock.move_to(datetime.fromisoformat("2026-10-05T12:00:00+04:00"))

        slots = self.query(cabinet, 2, full_day=True)
        online = self.query(cabinet, 2, full_day=False)

        assert slots[:4] == [
            "12:00 Table 4",
            "12:00 Banquet hall",
            "12:30 Table 4",
            "12:30 Banquet hall",
        ]
        assert len(slots) > 10
        assert online[0] == "13:00 Table 4"
        assert len(online) == 10

    def test_ignores_the_online_party_limit(self) -> None:
        cabinet = Cabinet()

        assert self.query(cabinet, 30, full_day=True)[0].endswith("Banquet hall")
        with pytest.raises(ValidationFailedError):
            self.query(cabinet, 30, full_day=False)

    def test_lists_every_free_stay(self) -> None:
        cabinet = Cabinet()
        for number in range(1, 13):
            cabinet.world.add_resource(
                cabinet.business,
                f"Room {number:02d}",
                kind=cabinet.table.kind,
                booking_unit=BookingUnit.NIGHT,
            )

        result = cabinet.world.check_availability().run(
            AvailabilityQuery(
                business_id=cabinet.business.id,
                date=LocalDate("2026-10-06"),
                nights=NightCount(2),
                full_day=True,
            )
        )

        stays = [
            slot for slot in result.slots if slot.booking_unit is BookingUnit.NIGHT
        ]
        assert len(stays) == 12


def every_day_until(closes: str) -> list[OpeningInterval]:
    return every_day("12:00", closes)

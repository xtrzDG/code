"""Booking updates from the cabinet: status changes and edits of the details."""

import pytest

from app.schemas.constants.bookings import (
    BookingStatus,
    BookingUnit,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.bookings import AvailabilityQuery, BookingView
from app.schemas.dto.operations.bookings import (
    UpdateBookingCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.contacts.strings import ContactName
from tests.operations.builders import every_day
from tests.operations.cabinet_bookings_helpers import Cabinet


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


def every_day_until(closes: str) -> list[OpeningInterval]:
    return every_day("12:00", closes)

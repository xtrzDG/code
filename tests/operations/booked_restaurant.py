"""
A Tbilisi restaurant where two customers already booked, for cancel and move tests.
"""

from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.bookings import CancelBookingCommand, RescheduleBookingCommand
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.operations.operations_world import OperationsWorld

PHONE: str = "+995555123456"


class BookedRestaurant:
    """Tbilisi restaurant where two customers already booked."""

    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.business = self.world.add_business()
        self.world.add_profile(self.business)
        self.world.add_resource(self.business, "Table 2", capacity=2)
        self.table_for_four = self.world.add_resource(
            self.business, "Table 4", capacity=4
        )
        self.table_for_eight = self.world.add_resource(
            self.business, "Table 8", capacity=8
        )
        self.customer = self.world.add_contact(self.business, "Giorgi", PHONE)
        self.other_customer = self.world.add_contact(
            self.business, "Tamar", "+995599765432"
        )
        self.dinner: BookingDocument = self.world.add_booking(
            self.business,
            self.table_for_four,
            self.customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
            party_size=4,
        )
        self.lunch: BookingDocument = self.world.add_booking(
            self.business,
            self.table_for_four,
            self.customer,
            "2026-10-08T13:00:00+04:00",
            "2026-10-08T15:00:00+04:00",
            party_size=4,
        )
        self.other_dinner: BookingDocument = self.world.add_booking(
            self.business,
            self.table_for_eight,
            self.other_customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
            party_size=6,
        )

    def cancel(
        self,
        booking_id: BookingId | None = None,
        contact_id: ContactId | None = None,
        phone: str | None = None,
        day: str | None = None,
        language: str = "ru",
    ) -> str:
        result = self.world.cancel_booking().run(
            CancelBookingCommand(
                business_id=self.business.id,
                booking_id=booking_id,
                contact_id=contact_id,
                contact_phone_number=None if phone is None else E164PhoneNumber(phone),
                date=None if day is None else LocalDate(day),
                language=LanguageTag(language),
            )
        )
        return str(result.confirmation_text)

    def reschedule(
        self,
        new_date: str,
        new_time: str | None,
        booking_id: BookingId | None = None,
        contact_id: ContactId | None = None,
        old_date: str | None = None,
        language: str = "en",
    ) -> str:
        result = self.world.reschedule_booking().run(
            RescheduleBookingCommand(
                business_id=self.business.id,
                booking_id=booking_id,
                contact_id=contact_id,
                old_date=None if old_date is None else LocalDate(old_date),
                new_date=LocalDate(new_date),
                new_time=None if new_time is None else LocalTimeOfDay(new_time),
                language=LanguageTag(language),
            )
        )
        return str(result.confirmation_text)

    def stored(self, booking: BookingDocument) -> BookingDocument:
        found = self.world.booking_repo.get(self.business.id, booking.id)
        assert found is not None
        return found

"""The full evening after Giorgi cancelled: Nino holds the place, Tamar waits."""

from datetime import UTC, datetime, timedelta

from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.bookings import CancelBookingCommand
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId
from tests.waitlist.full_evening import DAY, FullEvening


class OfferedEvening(FullEvening):
    """Nino (ru) waits first and is offered the freed 19:00; Tamar (ka) waits next."""

    def __init__(self) -> None:
        super().__init__()
        world = self.world
        self.nino = world.guest("Nino", "ru")
        self.nino_chat = world.telegram_conversation(self.nino)
        self.nino_entry: WaitlistEntryId = world.join(
            self.nino, self.nino_chat, DAY, "19:00", "21:00"
        ).entry_id
        self.tamar = world.guest("Tamar", "ka")
        self.tamar_chat = world.telegram_conversation(self.tamar)
        self.tamar_entry: WaitlistEntryId = world.join(
            self.tamar, self.tamar_chat, DAY, "19:00", "21:00"
        ).entry_id
        world.cancel_booking().run(
            CancelBookingCommand(
                business_id=world.business.id,
                booking_id=self.evening.id,
                contact_id=self.giorgi.id,
                language=LanguageTag("ka"),
            )
        )
        world.run_offer_jobs()

    def pass_minutes(self, minutes: int) -> None:
        now = datetime.fromtimestamp(
            int(self.world.clock.now_microseconds()) / 1_000_000, UTC
        )
        self.world.clock.move_to(now + timedelta(minutes=minutes))

    def evening_bookings(self) -> list[BookingDocument]:
        """The live bookings of Table 4 that start at 19:00."""

        return [
            booking
            for booking in self.world.bookings_of(self.world.business.id)
            if booking.resource_id == self.world.table_for_four.id
            and booking.starts_at == self.evening.starts_at
            and booking.status is not BookingStatus.CANCELLED
        ]

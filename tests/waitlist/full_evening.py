"""Wednesday 7 October at the restaurant, with every table taken all day."""

from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from tests.waitlist.waitlist_world import WaitlistWorld

DAY: str = "2026-10-07"
OFFSET: str = "+04:00"


def at(time: str) -> str:
    return f"{DAY}T{time}:00{OFFSET}"


class FullEvening:
    """
    Both tables are booked from opening to closing; on Table 4 the evening
    from 19:00 to 21:00 is Giorgi's, the booking a cancellation frees.
    """

    def __init__(self, world: WaitlistWorld | None = None) -> None:
        self.world = world or WaitlistWorld()
        self.regular: ContactDocument = self.world.guest("Regular", "ka")
        self.giorgi: ContactDocument = self.world.guest("Giorgi", "ka")
        self.giorgi_chat = self.world.telegram_conversation(self.giorgi)
        table = self.world.table_for_four
        self.book(table, self.regular, "12:00", "19:00")
        self.evening: BookingDocument = self.book(table, self.giorgi, "19:00", "21:00")
        self.book(table, self.regular, "21:00", "23:00")
        self.book(self.world.table_for_eight, self.regular, "12:00", "23:00", 6)

    def book(
        self,
        table: ResourceDocument,
        guest: ContactDocument,
        starts: str,
        ends: str,
        party_size: int = 2,
    ) -> BookingDocument:
        booking = self.world.add_booking(
            self.world.business,
            table,
            guest,
            at(starts),
            at(ends),
            party_size=party_size,
        )
        booking.conversation_id = None
        return booking

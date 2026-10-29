"""A Tbilisi restaurant with a table and a customer, ready to take bookings."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import BookingResult, CreateBookingCommand
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.operations.operations_world import OperationsWorld


class Restaurant:
    def __init__(self, world: OperationsWorld | None = None) -> None:
        self.world = world or OperationsWorld()
        self.business: BusinessDocument = self.world.add_business()
        self.world.add_profile(self.business)
        self.world.add_resource(self.business, "Table 2", capacity=2)
        self.table_for_four = self.world.add_resource(
            self.business, "Table 4", capacity=4
        )
        self.world.add_resource(self.business, "Table 8", capacity=8)
        self.contact: ContactDocument = self.world.add_contact(self.business)

    def command(
        self,
        time: str | None = "19:00",
        day: str = "2026-10-06",
        party_size: int = 4,
        language: str = "ka",
        is_sandbox: bool = False,
        contact_id: ContactId | None = None,
        name: str = "Giorgi Beridze",
        phone: str | None = "+995555123456",
    ) -> CreateBookingCommand:
        return CreateBookingCommand(
            business_id=self.business.id,
            contact_id=contact_id or self.contact.id,
            conversation_id=ConversationId(),
            contact_name=ContactName(name),
            contact_phone_number=None if phone is None else E164PhoneNumber(phone),
            date=LocalDate(day),
            time=None if time is None else LocalTimeOfDay(time),
            party_size=PartySize(party_size),
            notes=BookingNote("Window seat"),
            source_channel=ChannelKind.WHATSAPP,
            language=LanguageTag(language),
            is_sandbox=is_sandbox,
        )

    def book(self, command: CreateBookingCommand) -> BookingResult:
        return self.world.create_booking().run(command)

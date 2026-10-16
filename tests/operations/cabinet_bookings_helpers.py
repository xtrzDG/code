"""A cabinet over the operations world: a business, places and booking commands."""

from app.schemas.constants.bookings import BookingOrder, BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.operations.bookings import (
    BookingPage,
    ListBookingsQuery,
    ManualBookingCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.operations_world import OperationsWorld


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

"""
A Tbilisi guest house whose rooms belong to priced room types.

Rooms 101 and 102 are Deluxe rooms (200 GEL a night; 300 GEL in the
summer, July 1 to August 31; 350 GEL over the holidays, December 20 to
January 10); room 201 is a Standard room (120 GEL a night all year).
Check-in 14:00, check-out 12:00. Now is Monday 2026-10-05.
"""

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument, SeasonalNightlyRate
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    CreateBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.dto.knowledge import PriceLookupQuery, PriceLookupResult
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import NightCount, PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.knowledge.constrained_integers import NightlyRateMinor
from app.schemas.typings.knowledge.constrained_strings import SeasonDay
from app.schemas.typings.knowledge.strings import (
    KnowledgeTitle,
    SeasonName,
    ServiceReference,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.knowledge.get_price_use_case import GetPriceUseCase
from tests.operations.operations_world import OperationsWorld

SUMMER = ("07-01", "08-31", 30000, "Summer")
HOLIDAYS = ("12-20", "01-10", 35000, "Holidays")


def season(starts: str, ends: str, rate: int, name: str) -> SeasonalNightlyRate:
    return SeasonalNightlyRate(
        starts_on=SeasonDay(starts),
        ends_on=SeasonDay(ends),
        nightly_rate_minor=NightlyRateMinor(rate),
        name=SeasonName(name),
    )


class GuestHouse:
    def __init__(self) -> None:
        self.world: OperationsWorld = OperationsWorld()
        self.business: BusinessDocument = self.world.add_business(
            name="Old Town Rooms", niche_key=NicheKey.HOTEL
        )
        self.world.add_profile(
            self.business,
            resource_kind=ResourceKind.ROOM,
            min_notice_minutes=0,
            max_party_size=4,
            niche_answers={"check_in_time": "14:00", "check_out_time": "12:00"},
        )
        self.deluxe: KnowledgeItemDocument = self.room_type(
            "Deluxe room", 20000, [season(*SUMMER), season(*HOLIDAYS)]
        )
        self.standard: KnowledgeItemDocument = self.room_type("Standard room", 12000)
        self.room_101: ResourceDocument = self.room("Room 101", self.deluxe)
        self.room_102: ResourceDocument = self.room("Room 102", self.deluxe)
        self.room_201: ResourceDocument = self.room("Room 201", self.standard)
        self.contact: ContactDocument = self.world.add_contact(self.business, "Lena")

    def room_type(
        self,
        title: str,
        rate: int | None,
        seasons: list[SeasonalNightlyRate] | None = None,
    ) -> KnowledgeItemDocument:
        item = KnowledgeItemDocument(
            business_id=self.business.id,
            kind=KnowledgeItemKind.ROOM_TYPE,
            title=KnowledgeTitle(title),
            price_minor=None if rate is None else MoneyAmountMinor(rate),
            currency_code=self.business.currency_code,
            seasonal_rates=seasons or [],
        )
        self.world.knowledge_repo.save(item)
        return item

    def room(self, name: str, room_type: KnowledgeItemDocument) -> ResourceDocument:
        resource = self.world.add_resource(
            self.business,
            name,
            capacity=2,
            kind=ResourceKind.ROOM,
            booking_unit=BookingUnit.NIGHT,
        ).model_copy(update={"room_type_item_id": room_type.id})
        self.world.resource_repo.save(resource)
        return resource

    def query(
        self,
        day: str,
        nights: int,
        service: str | None = None,
        resource_id: ResourceId | None = None,
    ) -> AvailabilityResult:
        return self.world.check_availability().run(
            AvailabilityQuery(
                business_id=self.business.id,
                date=LocalDate(day),
                nights=NightCount(nights),
                party_size=PartySize(2),
                service_reference=None
                if service is None
                else ServiceReference(service),
                resource_id=resource_id,
            )
        )

    def book(
        self,
        day: str,
        nights: int,
        service: str | None = "deluxe room",
        resource_id: ResourceId | None = None,
    ) -> BookingResult:
        return self.world.create_booking().run(
            CreateBookingCommand(
                business_id=self.business.id,
                contact_id=self.contact.id,
                contact_name=ContactName("Lena Weber"),
                service_reference=None
                if service is None
                else ServiceReference(service),
                resource_id=resource_id,
                date=LocalDate(day),
                nights=NightCount(nights),
                party_size=PartySize(2),
                source_channel=ChannelKind.WEB_CHAT,
                language=LanguageTag("en"),
            )
        )

    def reschedule_command(
        self, booking_id: BookingId, day: str
    ) -> RescheduleBookingCommand:
        return RescheduleBookingCommand(
            business_id=self.business.id,
            booking_id=booking_id,
            new_date=LocalDate(day),
            language=LanguageTag("en"),
        )

    def price(
        self, name: str, check_in: str | None = None, nights: int | None = None
    ) -> PriceLookupResult:
        return GetPriceUseCase(
            business_repo=self.world.business_repo,
            knowledge_item_repo=self.world.knowledge_repo,
        ).run(
            PriceLookupQuery(
                business_id=self.business.id,
                item_name=KnowledgeTitle(name),
                language=LanguageTag("en"),
                check_in=None if check_in is None else LocalDate(check_in),
                nights=None if nights is None else NightCount(nights),
            )
        )

"""
A Tbilisi beauty salon whose masters perform their own services.

Open 10:00-20:00 every day, one hour of notice, staff booked by time.
Nino and Levan cut hair (Haircut: 45 minutes plus a 15-minute buffer,
45 GEL; linked on the service's side); Mariam does nails (Manicure: 60
minutes, 30 GEL; linked on Mariam's side). Now is Monday 2026-10-05,
12:00 in Tbilisi.
"""

from collections.abc import Sequence

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    CreateBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import ResourceReference
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
    ServiceDurationMinutes,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle, ServiceReference
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.builders import every_day
from tests.operations.operations_world import OperationsWorld

TOMORROW: str = "2026-10-06"


class Salon:
    def __init__(self, world: OperationsWorld | None = None) -> None:
        self.world: OperationsWorld = world or OperationsWorld()
        self.business: BusinessDocument = self.world.add_business(
            name="Salon Tsiskari", niche_key=NicheKey.BEAUTY_SALON
        )
        self.world.add_profile(
            self.business,
            hours=every_day("10:00", "20:00"),
            resource_kind=ResourceKind.STAFF,
            slot_minutes=60,
            max_party_size=1,
        )
        self.nino: ResourceDocument = self.staff("Nino")
        self.levan: ResourceDocument = self.staff("Levan")
        self.manicure: KnowledgeItemDocument = self.offer("Manicure", 60, 3000)
        self.mariam: ResourceDocument = self.staff("Mariam", serves=[self.manicure])
        self.haircut: KnowledgeItemDocument = self.offer(
            "Haircut", 45, 4500, buffer=15, performers=[self.nino, self.levan]
        )
        self.contact: ContactDocument = self.world.add_contact(self.business, "Ana")

    def staff(
        self, name: str, serves: Sequence[KnowledgeItemDocument] = ()
    ) -> ResourceDocument:
        resource = self.world.add_resource(
            self.business, name, capacity=1, kind=ResourceKind.STAFF
        ).model_copy(update={"serves_item_ids": [item.id for item in serves]})
        self.world.resource_repo.save(resource)
        return resource

    def offer(
        self,
        title: str,
        minutes: int,
        price_minor: int,
        buffer: int | None = None,
        performers: Sequence[ResourceDocument] = (),
        kind: KnowledgeItemKind = KnowledgeItemKind.SERVICE,
    ) -> KnowledgeItemDocument:
        item = KnowledgeItemDocument(
            business_id=self.business.id,
            kind=kind,
            title=KnowledgeTitle(title),
            price_minor=MoneyAmountMinor(price_minor),
            currency_code=self.business.currency_code,
            duration_minutes=ServiceDurationMinutes(minutes),
            buffer_minutes=None if buffer is None else BufferMinutes(buffer),
            performer_resource_ids=[performer.id for performer in performers],
        )
        self.world.knowledge_repo.save(item)
        return item

    def query(
        self,
        service: str | None = None,
        resource: str | None = None,
        time: str | None = "12:00",
        day: str = TOMORROW,
        resource_id: ResourceId | None = None,
        service_item_id: KnowledgeItemId | None = None,
    ) -> AvailabilityResult:
        return self.world.check_availability().run(
            AvailabilityQuery(
                business_id=self.business.id,
                date=LocalDate(day),
                time=None if time is None else LocalTimeOfDay(time),
                party_size=PartySize(1),
                service_reference=None
                if service is None
                else ServiceReference(service),
                resource_reference=(
                    None if resource is None else ResourceReference(resource)
                ),
                resource_id=resource_id,
                service_item_id=service_item_id,
            )
        )

    def book(
        self,
        service: str | None = "Haircut",
        resource: str | None = None,
        time: str = "12:00",
        day: str = TOMORROW,
    ) -> BookingResult:
        return self.world.create_booking().run(
            CreateBookingCommand(
                business_id=self.business.id,
                contact_id=self.contact.id,
                contact_name=ContactName("Ana Kapanadze"),
                service_reference=None
                if service is None
                else ServiceReference(service),
                resource_reference=(
                    None if resource is None else ResourceReference(resource)
                ),
                date=LocalDate(day),
                time=LocalTimeOfDay(time),
                party_size=PartySize(1),
                source_channel=ChannelKind.WHATSAPP,
                language=LanguageTag("en"),
            )
        )

    def reschedule(
        self, booking_id: BookingId, time: str, day: str = TOMORROW
    ) -> BookingResult:
        return self.world.reschedule_booking().run(
            RescheduleBookingCommand(
                business_id=self.business.id,
                booking_id=booking_id,
                new_date=LocalDate(day),
                new_time=LocalTimeOfDay(time),
                language=LanguageTag("en"),
            )
        )


def reason_code(error: ValidationFailedError) -> str:
    """The code of the error's only reason."""

    assert len(error.reasons) == 1
    return str(error.reasons[0].code)

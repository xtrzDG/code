"""
The salon's services and who performs them. Each stylist offers only her
or his own, so "Balayage bei Lena" books Lena for three hours and a lash
lift never lands on Mehmet; the break between appointments is the buffer.
"""

from collections.abc import Sequence
from typing import NamedTuple

from typed_time_provider import Microseconds

from app.registries.demo.demo_foundation_parts import knowledge_item
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument

LENA: str = "Lena"
MEHMET: str = "Mehmet"
SOFIA: str = "Sofia"
# The owner's answer to "break between appointments", in minutes.
BREAK_MINUTES: int = 10


class SalonService(NamedTuple):
    title: str
    price_minor: int
    minutes: int
    performer: str
    body: str | None = None


SALON_SERVICES: tuple[SalonService, ...] = (
    SalonService("Damenhaarschnitt & Föhnen", 6500, 60, LENA),
    SalonService("Herrenhaarschnitt", 3500, 30, MEHMET),
    SalonService("Bartpflege & Nassrasur", 2500, 30, MEHMET),
    SalonService(
        "Balayage",
        16000,
        180,
        LENA,
        "Inklusive Pflege und Föhnen; Preis für mittellanges Haar.",
    ),
    SalonService("Ansatzfarbe", 7000, 90, LENA),
    SalonService("Maniküre mit Shellac", 4200, 60, SOFIA),
    SalonService("Wimpernlifting", 5500, 60, SOFIA),
    SalonService("Augenbrauen zupfen & färben", 2500, 30, SOFIA),
)


def build_salon_services(
    business: BusinessDocument, since: Microseconds
) -> list[KnowledgeItemDocument]:
    """The price list as service items, in the order of `SALON_SERVICES`."""

    return [
        knowledge_item(
            business,
            KnowledgeItemKind.SERVICE,
            service.title,
            since,
            body=service.body,
            price_minor=service.price_minor,
            duration_minutes=service.minutes,
            buffer_minutes=BREAK_MINUTES,
        )
        for service in SALON_SERVICES
    ]


def services_of(
    performer: str, services: Sequence[KnowledgeItemDocument]
) -> list[KnowledgeItemDocument]:
    """The items of `services` that `performer` offers."""

    titles: set[str] = {
        service.title for service in SALON_SERVICES if service.performer == performer
    }
    return [item for item in services if str(item.title) in titles]

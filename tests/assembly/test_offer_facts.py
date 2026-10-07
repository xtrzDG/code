"""The fact table names who performs a service, its break and nightly seasons."""

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument, SeasonalNightlyRate
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    ResourceCapacity,
    ResourceUnitCount,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
    NightlyRateMinor,
    ServiceDurationMinutes,
)
from app.schemas.typings.knowledge.constrained_strings import SeasonDay
from app.schemas.typings.knowledge.strings import KnowledgeTitle, SeasonName
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.assembly.fact_descriptions import (
    describe_knowledge_item,
    describe_resource,
)
from app.utilities.assembly.offer_facts import offer_titles, performer_names

BUSINESS = BusinessId()
GEL = CurrencyCode("GEL")


def staff(name: str, is_active: bool = True) -> ResourceDocument:
    return ResourceDocument(
        business_id=BUSINESS,
        kind=ResourceKind.STAFF,
        name=ResourceName(name),
        capacity=ResourceCapacity(1),
        unit_count=ResourceUnitCount(1),
        booking_unit=BookingUnit.TIME_SLOT,
        is_active=is_active,
    )


def offer(title: str, **fields: object) -> KnowledgeItemDocument:
    return KnowledgeItemDocument.model_validate(
        {
            "business_id": BUSINESS,
            "kind": KnowledgeItemKind.SERVICE,
            "title": KnowledgeTitle(title),
            **fields,
        }
    )


def test_a_service_fact_names_its_length_break_and_masters() -> None:
    nino, levan, gone = staff("Nino"), staff("Levan"), staff("Gone", is_active=False)
    haircut = offer(
        "Haircut",
        price_minor=MoneyAmountMinor(4500),
        duration_minutes=ServiceDurationMinutes(45),
        buffer_minutes=BufferMinutes(15),
        performer_resource_ids=[nino.id, gone.id],
    )
    levan = levan.model_copy(update={"serves_item_ids": [haircut.id]})

    names = performer_names(haircut, [nino, levan, gone])
    text = describe_knowledge_item(haircut, GEL, names)

    assert names == ["Nino", "Levan"]
    assert "Duration: 45 min" in text
    assert "Break after it: 15 min" in text
    assert text.endswith("Performed by: Nino, Levan")


def test_a_master_fact_lists_what_she_performs() -> None:
    mariam = staff("Mariam")
    manicure = offer("Manicure", performer_resource_ids=[mariam.id])
    pedicure = offer("Pedicure")
    retired = offer("Waxing", is_active=False)
    mariam = mariam.model_copy(update={"serves_item_ids": [pedicure.id, retired.id]})

    titles = offer_titles(mariam, [manicure, pedicure, retired])

    assert titles == ["Pedicure", "Manicure"]
    assert describe_resource(mariam, None, titles).endswith(
        "Performs: Pedicure, Manicure"
    )


def test_a_room_type_fact_lists_its_seasonal_nightly_rates() -> None:
    deluxe = offer(
        "Deluxe room",
        kind=KnowledgeItemKind.ROOM_TYPE,
        price_minor=MoneyAmountMinor(20000),
        seasonal_rates=[
            SeasonalNightlyRate(
                starts_on=SeasonDay("07-01"),
                ends_on=SeasonDay("08-31"),
                nightly_rate_minor=NightlyRateMinor(30000),
                name=SeasonName("Summer"),
            )
        ],
    )

    text = describe_knowledge_item(deluxe, GEL)

    assert "Nightly rate by season: 07-01 to 08-31" in text
    assert "(Summer)" in text

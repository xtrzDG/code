"""A niche's own booking autotests: a named master, a room type for N nights."""

from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import BookingScenarioVariant, NicheKey
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.bookings.constrained_integers import (
    ResourceCapacity,
    ResourceUnitCount,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.utilities.assembly.booking_variant_scenarios import (
    plan_variant_goals,
    plan_variant_scenarios,
)
from tests.assembly.test_autotest_scenarios import ENGLISH, GEORGIAN

BUSINESS = BusinessId()
SPECIFIC = BookingScenarioVariant.SPECIFIC_PERFORMER
STAY = BookingScenarioVariant.ROOM_TYPE_STAY


def resource(name: str, unit: BookingUnit = BookingUnit.TIME_SLOT) -> ResourceDocument:
    return ResourceDocument(
        business_id=BUSINESS,
        kind=ResourceKind.ROOM if unit is BookingUnit.NIGHT else ResourceKind.STAFF,
        name=ResourceName(name),
        capacity=ResourceCapacity(2),
        unit_count=ResourceUnitCount(1),
        booking_unit=unit,
    )


def offer(
    title: str, kind: KnowledgeItemKind, **fields: object
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument.model_validate(
        {
            "business_id": BUSINESS,
            "kind": kind,
            "title": KnowledgeTitle(title),
            **fields,
        }
    )


def test_a_salon_tests_a_haircut_with_the_master_who_does_it() -> None:
    nino, mariam = resource("Nino"), resource("Mariam")
    items = [
        offer(
            "Manicure", KnowledgeItemKind.SERVICE, performer_resource_ids=[mariam.id]
        ),
        offer("Coffee", KnowledgeItemKind.MENU_ITEM),
    ]

    goals = plan_variant_goals([SPECIFIC], items, [nino, mariam])

    assert len(goals) == 1
    assert '"Manicure"' in goals[0] and "with Mariam" in goals[0]


def test_a_hotel_tests_a_room_type_for_three_nights() -> None:
    deluxe = offer("Deluxe room", KnowledgeItemKind.ROOM_TYPE)
    room = resource("Room 101", BookingUnit.NIGHT).model_copy(
        update={"room_type_item_id": deluxe.id}
    )

    goals = plan_variant_goals([STAY, SPECIFIC], [deluxe], [room])

    assert len(goals) == 1
    assert '"Deluxe room" for 3 nights' in goals[0]
    assert "whole stay costs" in goals[0]


def test_variants_the_business_has_nothing_for_are_left_out() -> None:
    lonely_room_type = offer("Suite", KnowledgeItemKind.ROOM_TYPE)

    assert plan_variant_goals([STAY, SPECIFIC], [lonely_room_type], []) == []
    assert plan_variant_goals([SPECIFIC], [], [resource("Nino")]) == []


def test_variant_scenarios_are_bookings_keyed_after_the_base_one() -> None:
    goals = plan_variant_goals(
        [SPECIFIC, STAY],
        [
            offer("Haircut", KnowledgeItemKind.SERVICE),
            deluxe := offer("Deluxe room", KnowledgeItemKind.ROOM_TYPE),
        ],
        [
            resource("Nino"),
            resource("Room 101", BookingUnit.NIGHT).model_copy(
                update={"room_type_item_id": deluxe.id}
            ),
        ],
    )

    scenarios = plan_variant_scenarios([GEORGIAN, ENGLISH], goals)

    assert [str(scenario.key) for scenario in scenarios] == [
        "booking__ka__2",
        "booking__en__3",
    ]
    assert {scenario.kind for scenario in scenarios} == {AutotestScenarioKind.BOOKING}
    assert plan_variant_scenarios([], goals) == []


def test_niches_declare_their_booking_variants() -> None:
    registry = NicheTemplateRegistry()

    assert registry.get(NicheKey.BEAUTY_SALON).booking_variants == [SPECIFIC]
    assert registry.get(NicheKey.HOTEL).booking_variants == [STAY]
    assert registry.get(NicheKey.RESTAURANT).booking_variants == []

"""
Offers and their performers, linked from either editor: what each side
shows, how saving one side unlinks the other, and which links are refused.
"""

import pytest

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemDetails,
    KnowledgeItemInput,
    KnowledgeItemPatch,
    KnowledgeItemQuery,
    UpdateKnowledgeItemCommand,
)
from app.schemas.dto.resources import (
    ResourceListQuery,
    ResourcePatch,
    ResourceView,
    UpdateResourceCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
    ServiceDurationMinutes,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.resource_helpers import add_resource


def add_service(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    title: str,
    performers: list[ResourceId] | None = None,
    buffer: int | None = None,
    kind: KnowledgeItemKind = KnowledgeItemKind.SERVICE,
) -> KnowledgeItemDetails:
    return harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=kind,
                title=KnowledgeTitle(title),
                price_minor=MoneyAmountMinor(4500),
                duration_minutes=ServiceDurationMinutes(45),
                buffer_minutes=None if buffer is None else BufferMinutes(buffer),
                performer_resource_ids=performers or [],
            ),
        )
    )


def item(
    harness: KnowledgeHarness, business: BusinessDocument, item_id: KnowledgeItemId
) -> KnowledgeItemDetails:
    return harness.get_knowledge_item.run(
        KnowledgeItemQuery(business_id=business.id, item_id=item_id)
    )


def resource(
    harness: KnowledgeHarness, business: BusinessDocument, resource_id: ResourceId
) -> ResourceView:
    views = harness.list_resources.run(ResourceListQuery(business_id=business.id))
    return next(view for view in views.items if view.id == resource_id)


def salon() -> tuple[KnowledgeHarness, BusinessDocument]:
    harness = KnowledgeHarness()
    return harness, harness.add_business(niche_key=NicheKey.BEAUTY_SALON)


def test_a_service_names_its_masters_and_the_masters_show_it() -> None:
    harness, business = salon()
    nino = add_resource(harness, business, "Nino", capacity=1)

    haircut = add_service(harness, business, "Haircut", [nino.id], buffer=15)

    assert haircut.performer_resource_ids == [nino.id]
    assert haircut.buffer_minutes == 15
    assert resource(harness, business, nino.id).serves_item_ids == [haircut.id]


def test_a_master_names_her_services_and_the_service_shows_her() -> None:
    harness, business = salon()
    manicure = add_service(harness, business, "Manicure")

    mariam = add_resource(
        harness, business, "Mariam", capacity=1, serves_item_ids=[manicure.id]
    )

    assert mariam.serves_item_ids == [manicure.id]
    assert item(harness, business, manicure.id).performer_resource_ids == [mariam.id]


def test_saving_the_services_list_unlinks_the_service_side_too() -> None:
    harness, business = salon()
    nino = add_resource(harness, business, "Nino", capacity=1)
    haircut = add_service(harness, business, "Haircut", [nino.id])

    harness.update_resource.run(
        UpdateResourceCommand(
            business_id=business.id,
            resource_id=nino.id,
            patch=ResourcePatch(serves_item_ids=[]),
        )
    )

    assert item(harness, business, haircut.id).performer_resource_ids == []
    assert resource(harness, business, nino.id).serves_item_ids == []


def test_saving_the_performers_list_unlinks_the_master_side_too() -> None:
    harness, business = salon()
    manicure = add_service(harness, business, "Manicure")
    mariam = add_resource(
        harness, business, "Mariam", capacity=1, serves_item_ids=[manicure.id]
    )
    nino = add_resource(harness, business, "Nino", capacity=1)

    updated = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=manicure.id,
            patch=KnowledgeItemPatch(performer_resource_ids=[nino.id]),
        )
    )

    assert updated.performer_resource_ids == [nino.id]
    assert resource(harness, business, mariam.id).serves_item_ids == []
    assert resource(harness, business, nino.id).serves_item_ids == [manicure.id]


def test_an_unknown_performer_is_refused() -> None:
    harness, business = salon()

    with pytest.raises(ValidationFailedError, match="do not exist"):
        add_service(harness, business, "Haircut", [ResourceId()])


def test_a_master_serves_only_services_and_packages_of_the_business() -> None:
    harness, business = salon()
    faq = add_service(
        harness, business, "Do you take cards?", kind=KnowledgeItemKind.FAQ
    )

    with pytest.raises(ValidationFailedError, match="services and packages"):
        add_resource(harness, business, "Nino", capacity=1, serves_item_ids=[faq.id])
    with pytest.raises(ValidationFailedError, match="services and packages"):
        add_resource(
            harness, business, "Levan", capacity=1, serves_item_ids=[KnowledgeItemId()]
        )


def test_a_room_belongs_to_a_room_type_only() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.HOTEL)
    deluxe = add_service(
        harness, business, "Deluxe room", kind=KnowledgeItemKind.ROOM_TYPE
    )
    breakfast = add_service(
        harness, business, "Breakfast", kind=KnowledgeItemKind.SERVICE
    )

    room = add_resource(harness, business, "Room 101", room_type_item_id=deluxe.id)

    assert room.room_type_item_id == deluxe.id
    assert item(harness, business, deluxe.id).performer_resource_ids == [room.id]
    with pytest.raises(ValidationFailedError, match="not a room type"):
        add_resource(harness, business, "Room 102", room_type_item_id=breakfast.id)

    # Leaving the room out of the type's list takes the room out of the type.
    harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=deluxe.id,
            patch=KnowledgeItemPatch(performer_resource_ids=[]),
        )
    )
    assert resource(harness, business, room.id).room_type_item_id is None

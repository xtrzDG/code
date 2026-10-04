"""
The links between offers and the resources that perform them, as the
cabinet edits them from either side.

The owner links a master and a service on the service ("who performs it")
or on the master ("services"), and a room to its room type on the room.
Both editors show every link, from either side; saving one side's list
makes it the whole truth: a link left out is removed on the other side
too, so a link never survives on one side after the owner removed it on
the other.
"""

from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.utilities.bookings.bookable_offers import BOOKABLE_KINDS, is_linked


def linked_performer_ids(
    item: KnowledgeItemDocument,
    resources: Sequence[ResourceDocument],
) -> list[ResourceId]:
    """The resources linked to the item from either side (its own list first)."""

    linked: list[ResourceId] = list(dict.fromkeys(item.performer_resource_ids))
    linked.extend(
        resource.id
        for resource in sorted(resources, key=lambda resource: str(resource.name))
        if resource.id not in linked and is_linked(item, resource)
    )
    return linked


def linked_service_ids(
    resource: ResourceDocument,
    items: Sequence[KnowledgeItemDocument],
) -> list[KnowledgeItemId]:
    """The services and packages linked to the resource from either side."""

    linked: list[KnowledgeItemId] = list(dict.fromkeys(resource.serves_item_ids))
    linked.extend(
        item.id
        for item in sorted(items, key=lambda item: str(item.title))
        if item.id not in linked
        and item.kind is not KnowledgeItemKind.ROOM_TYPE
        and resource.id in item.performer_resource_ids
    )
    return linked


def check_performer_ids(
    performer_ids: Sequence[ResourceId],
    resources: Sequence[ResourceDocument],
) -> list[ResourceId]:
    """
    The ids without repeats, each a resource of the business.

    Raises:
        ValidationFailedError: an id names no resource of the business.
    """

    known: set[ResourceId] = {resource.id for resource in resources}
    unknown: list[str] = [
        str(performer_id) for performer_id in performer_ids if performer_id not in known
    ]
    if unknown:
        raise ValidationFailedError(
            f"These resources do not exist in this business: {', '.join(unknown)}."
        )

    return list(dict.fromkeys(performer_ids))


def check_service_ids(
    item_ids: Sequence[KnowledgeItemId],
    items: Sequence[KnowledgeItemDocument],
) -> list[KnowledgeItemId]:
    """
    The ids without repeats, each a service or package of the business.

    Raises:
        ValidationFailedError: an id names no service or package.
    """

    offers: set[KnowledgeItemId] = {
        item.id
        for item in items
        if item.kind in BOOKABLE_KINDS and item.kind is not KnowledgeItemKind.ROOM_TYPE
    }
    unknown: list[str] = [str(item_id) for item_id in item_ids if item_id not in offers]
    if unknown:
        raise ValidationFailedError(
            "A resource performs services and packages of this business; not: "
            f"{', '.join(unknown)}."
        )

    return list(dict.fromkeys(item_ids))


def check_room_type_id(
    item_id: KnowledgeItemId | None,
    items: Sequence[KnowledgeItemDocument],
) -> KnowledgeItemId | None:
    """
    The room type of a room, an item of kind ROOM_TYPE of the business.

    Raises:
        ValidationFailedError: the id names no room type.
    """

    if item_id is None:
        return None

    if not any(
        item.id == item_id and item.kind is KnowledgeItemKind.ROOM_TYPE
        for item in items
    ):
        raise ValidationFailedError(f"{item_id} is not a room type of this business.")

    return item_id


def resources_to_unlink(
    item: KnowledgeItemDocument,
    resources: Sequence[ResourceDocument],
) -> list[ResourceDocument]:
    """
    The resources that still link to the item from their side although the
    item's new performer list leaves them out, with that link removed.
    """

    changed: list[ResourceDocument] = []
    for resource in resources:
        if resource.id in item.performer_resource_ids:
            continue

        is_serving: bool = item.id in resource.serves_item_ids
        is_of_type: bool = resource.room_type_item_id == item.id
        if not (is_serving or is_of_type):
            continue

        changed.append(
            resource.model_copy(
                update={
                    "serves_item_ids": [
                        served
                        for served in resource.serves_item_ids
                        if served != item.id
                    ],
                    "room_type_item_id": (
                        None if is_of_type else resource.room_type_item_id
                    ),
                }
            )
        )

    return changed


def items_to_unlink(
    resource: ResourceDocument,
    items: Sequence[KnowledgeItemDocument],
) -> list[KnowledgeItemDocument]:
    """
    The items that still name the resource as a performer although its new
    services (and room type) leave them out, with that link removed.
    """

    return [
        item.model_copy(
            update={
                "performer_resource_ids": [
                    performer
                    for performer in item.performer_resource_ids
                    if performer != resource.id
                ]
            }
        )
        for item in items
        if resource.id in item.performer_resource_ids
        and item.id not in resource.serves_item_ids
        and item.id != resource.room_type_item_id
    ]

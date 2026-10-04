"""Who performs what, as the fact table names it (active ones only)."""

from collections.abc import Sequence

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.assistants.assembly_sources import BusinessFactsSource
from app.utilities.assembly.fact_descriptions import (
    describe_knowledge_item,
    describe_resource,
)
from app.utilities.bookings.offer_links import (
    linked_performer_ids,
    linked_service_ids,
)


def performer_names(
    item: KnowledgeItemDocument,
    resources: Sequence[ResourceDocument],
) -> list[str]:
    """The active resources linked to the item, its own list first."""

    names: dict[str, str] = {
        str(resource.id): str(resource.name)
        for resource in resources
        if resource.is_active
    }
    return [
        names[str(performer_id)]
        for performer_id in linked_performer_ids(item, resources)
        if str(performer_id) in names
    ]


def offer_titles(
    resource: ResourceDocument,
    items: Sequence[KnowledgeItemDocument],
) -> list[str]:
    """The active services a resource performs, then its room type."""

    titles: dict[str, str] = {
        str(item.id): str(item.title) for item in items if item.is_active
    }
    linked: list[str] = [
        str(item_id) for item_id in linked_service_ids(resource, items)
    ]
    if resource.room_type_item_id is not None:
        linked.append(str(resource.room_type_item_id))

    return [titles[item_id] for item_id in linked if item_id in titles]


def describe_item_fact(item: KnowledgeItemDocument, source: BusinessFactsSource) -> str:
    """The fact value of a knowledge item, with who performs it."""

    return describe_knowledge_item(
        item, source.business.currency_code, performer_names(item, source.resources)
    )


def describe_resource_fact(
    resource: ResourceDocument, source: BusinessFactsSource
) -> str:
    """The fact value of a resource, with what it performs."""

    return describe_resource(
        resource,
        source.profile.booking_rules,
        offer_titles(resource, source.knowledge_items),
    )

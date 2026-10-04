"""
The resources linked to knowledge items (who performs a service, the
rooms of a room type): checked when an item names them, and removed on
the resources' side when the item's editor leaves them out.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.utilities.bookings.offer_links import check_performer_ids, resources_to_unlink


def check_item_performers(
    items: Sequence[KnowledgeItemDocument],
    resources: Sequence[ResourceDocument],
) -> None:
    """
    Raises:
        ValidationFailedError: an item names a resource the business lacks.
    """

    for item in items:
        check_performer_ids(item.performer_resource_ids, resources)


def unlink_left_out_resources(
    resource_repo: ResourceRepoContract,
    item: KnowledgeItemDocument,
    resources: Sequence[ResourceDocument],
    now: Microseconds,
) -> list[ResourceDocument]:
    """
    Save the resources whose link to the item the new performer list drops;
    returns every resource of the business as stored afterwards.
    """

    changed: dict[str, ResourceDocument] = {
        str(resource.id): resource.model_copy(update={"updated_at": now})
        for resource in resources_to_unlink(item, resources)
    }
    for resource in changed.values():
        resource_repo.save(resource)

    return [changed.get(str(resource.id), resource) for resource in resources]

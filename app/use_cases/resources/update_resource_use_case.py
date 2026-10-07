from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.resources import ResourceView, UpdateResourceCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.bookings.offer_links import items_to_unlink
from app.utilities.knowledge.resource_rules import patch_resource, to_resource_view


class UpdateResourceUseCase(UseCaseContract[UpdateResourceCommand, ResourceView]):
    """
    Change a resource of the business or switch it off (`is_active`).

    Resources are not deleted, so past bookings keep their resource. A
    resource of another business is reported as missing. A new list of
    services is the whole truth: a service left out stops naming the
    resource as its performer.
    """

    def __init__(
        self,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateResourceCommand) -> ResourceView:
        existing: ResourceDocument | None = self._resource_repo.get(
            input_data.business_id,
            input_data.resource_id,
        )
        if existing is None:
            raise NotFoundError(f"Resource {input_data.resource_id} was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        items: list[KnowledgeItemDocument] = self._knowledge_item_repo.list_by_business(
            input_data.business_id
        )
        updated: ResourceDocument = patch_resource(
            existing=existing,
            patch=input_data.patch,
            other_resources=[
                resource
                for resource in self._resource_repo.list_by_business(
                    input_data.business_id
                )
                if resource.id != existing.id
            ],
            now=now,
            items=items,
        )
        self._resource_repo.save(updated)
        if input_data.patch.serves_item_ids is not None:
            items = self._unlink_left_out_items(updated, items, now)

        return to_resource_view(updated, items)

    def _unlink_left_out_items(
        self,
        resource: ResourceDocument,
        items: list[KnowledgeItemDocument],
        now: Microseconds,
    ) -> list[KnowledgeItemDocument]:
        """Save the items that stop naming the resource; the items afterwards."""

        changed: dict[str, KnowledgeItemDocument] = {
            str(item.id): item.model_copy(update={"updated_at": now})
            for item in items_to_unlink(resource, items)
        }
        for item in changed.values():
            self._knowledge_item_repo.save(item)

        return [changed.get(str(item.id), item) for item in items]

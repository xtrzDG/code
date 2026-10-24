from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.use_cases.shared.knowledge_index_queue import queue_knowledge_index
from app.utilities.knowledge.imported_item_views import build_knowledge_item_view


class ConfirmImportedItemsUseCase(
    UseCaseContract[ConfirmImportedItemsCommand, ConfirmImportedItemsResult]
):
    """
    Activate the imported menu lines the owner checked, so the assistant may
    use them. Every id must be an imported item of this business; nothing is
    activated when one is not. Confirming an active item again is harmless.
    Newly confirmed items are indexed in the background (`index_knowledge`:
    aliases in the business's other languages, embeddings).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        knowledge_item_repo: KnowledgeItemRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: ConfirmImportedItemsCommand
    ) -> ConfirmImportedItemsResult:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        if not input_data.item_ids:
            raise ValidationFailedError("Choose at least one imported item.")

        items: list[KnowledgeItemDocument] = []
        for item_id in dict.fromkeys(input_data.item_ids):
            item: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
                business.id, item_id
            )
            if item is None:
                raise NotFoundError(f"Knowledge item {item_id} was not found.")

            if item.source is not KnowledgeItemSource.MENU_IMPORT:
                raise ValidationFailedError(
                    f"Knowledge item {item_id} was not imported from a menu."
                )

            items.append(item)

        now: Microseconds = self._wall_clock.now_unix()
        confirmed: int = 0
        for item in items:
            if not item.is_active or item.import_batch_id is not None:
                # A confirmed item no longer belongs to its import's drafts,
                # so discarding the import later keeps it.
                item.is_active = True
                item.import_batch_id = None
                item.updated_at = now
                self._knowledge_item_repo.save(item)
                confirmed += 1

        if confirmed > 0:
            queue_knowledge_index(self._job_queue, business.id)

        return ConfirmImportedItemsResult(
            business_id=business.id,
            activated_items=[
                build_knowledge_item_view(item, business.owner_language)
                for item in items
            ],
        )

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    DeleteKnowledgeItemCommand,
    KnowledgeItemDeletion,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.shared.knowledge_index_queue import queue_knowledge_index


class DeleteKnowledgeItemUseCase(
    UseCaseContract[DeleteKnowledgeItemCommand, KnowledgeItemDeletion]
):
    """
    Delete a knowledge item of the business; a foreign item is reported
    missing. The business's knowledge is queued for indexing again (its
    vector is forgotten).
    """

    def __init__(
        self,
        knowledge_item_repo: KnowledgeItemRepoContract,
        job_queue: JobQueueFacilitatorContract,
    ) -> None:
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue

    def run(self, input_data: DeleteKnowledgeItemCommand) -> KnowledgeItemDeletion:
        existing: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
            input_data.business_id,
            input_data.item_id,
        )
        if existing is None:
            raise NotFoundError(f"Knowledge item {input_data.item_id} was not found.")

        self._knowledge_item_repo.delete(input_data.business_id, input_data.item_id)
        queue_knowledge_index(self._job_queue, input_data.business_id)
        return KnowledgeItemDeletion(id=existing.id)

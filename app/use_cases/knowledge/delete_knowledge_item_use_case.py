from app.contracts.repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    DeleteKnowledgeItemCommand,
    KnowledgeItemDeletion,
)
from app.schemas.exceptions.application_errors import NotFoundError


class DeleteKnowledgeItemUseCase(
    UseCaseContract[DeleteKnowledgeItemCommand, KnowledgeItemDeletion]
):
    """Delete a knowledge item of the business; a foreign item is reported missing."""

    def __init__(self, knowledge_item_repo: KnowledgeItemRepoContract) -> None:
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: DeleteKnowledgeItemCommand) -> KnowledgeItemDeletion:
        existing: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
            input_data.business_id,
            input_data.item_id,
        )
        if existing is None:
            raise NotFoundError(f"Knowledge item {input_data.item_id} was not found.")

        self._knowledge_item_repo.delete(input_data.business_id, input_data.item_id)
        return KnowledgeItemDeletion(id=existing.id)

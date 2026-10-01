from app.contracts.repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.menu_import import (
    DiscardedImportBatch,
    DiscardImportBatchCommand,
)


class DiscardImportBatchUseCase(
    UseCaseContract[DiscardImportBatchCommand, DiscardedImportBatch]
):
    """
    Delete the drafts of one menu import the owner did not confirm ("discard
    all", or the unticked rest after confirming some). Only inactive
    MENU_IMPORT drafts that still carry the import's id are deleted;
    confirmed items left the batch when they were confirmed. Discarding an
    import with nothing left (or an unknown one) deletes nothing, so the
    request can be repeated safely.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: DiscardImportBatchCommand) -> DiscardedImportBatch:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        drafts: list[KnowledgeItemDocument] = [
            item
            for item in self._knowledge_item_repo.list_by_business(business.id)
            if item.import_batch_id == input_data.batch_id
            and item.source is KnowledgeItemSource.MENU_IMPORT
            and not item.is_active
        ]
        for draft in drafts:
            self._knowledge_item_repo.delete(business.id, draft.id)

        return DiscardedImportBatch(
            business_id=business.id,
            batch_id=input_data.batch_id,
            discarded_item_ids=[draft.id for draft in drafts],
        )

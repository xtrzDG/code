from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails, KnowledgeItemQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.knowledge_item_views import to_item_details


class GetKnowledgeItemUseCase(
    UseCaseContract[KnowledgeItemQuery, KnowledgeItemDetails]
):
    """Read one knowledge item of the business with its price formatted."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: KnowledgeItemQuery) -> KnowledgeItemDetails:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        item: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
            business.id,
            input_data.item_id,
        )
        if item is None:
            raise NotFoundError(f"Knowledge item {input_data.item_id} was not found.")

        return to_item_details(
            item,
            business.currency_code,
            input_data.language or business.owner_language,
        )

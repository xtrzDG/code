from app.contracts.repositories import BusinessRepoContract, KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemList, KnowledgeItemListQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.knowledge_items import item_sort_key, to_item_details


class ListKnowledgeItemsUseCase(
    UseCaseContract[KnowledgeItemListQuery, KnowledgeItemList]
):
    """List the knowledge base of a business, optionally by kind and active flag."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: KnowledgeItemListQuery) -> KnowledgeItemList:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        language: LanguageTag = input_data.language or business.owner_language
        items: list[KnowledgeItemDocument] = [
            item
            for item in self._knowledge_item_repo.list_by_business(business.id)
            if (input_data.kind is None or item.kind is input_data.kind)
            and (input_data.is_active is None or item.is_active == input_data.is_active)
        ]
        return KnowledgeItemList(
            items=[
                to_item_details(item, business.currency_code, language)
                for item in sorted(items, key=item_sort_key)
            ]
        )

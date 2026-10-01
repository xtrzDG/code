from app.contracts.repositories import BusinessRepoContract, KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemListQuery, KnowledgeItemPage
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.knowledge_items import to_item_details
from app.utilities.paging.cursor_paging import take_page


class ListKnowledgeItemsUseCase(
    UseCaseContract[KnowledgeItemListQuery, KnowledgeItemPage]
):
    """
    One page of the knowledge base of a business, newest first, optionally
    only one kind and only active or inactive items (filters apply before
    paging).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: KnowledgeItemListQuery) -> KnowledgeItemPage:
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
        page_items, next_cursor = take_page(
            items,
            input_data.page,
            sort_key=lambda item: int(item.created_at),
            item_id=lambda item: str(item.id),
        )
        return KnowledgeItemPage(
            items=[
                to_item_details(item, business.currency_code, language)
                for item in page_items
            ],
            next_cursor=next_cursor,
        )

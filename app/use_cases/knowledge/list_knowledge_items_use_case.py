from app.contracts.data_tasks import DataTaskRegistryContract, DataTaskStateRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.maintenance import IndexedList
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemListQuery, KnowledgeItemPage
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.list_indexing import read_list_indexing
from app.utilities.knowledge.knowledge_item_views import to_item_details
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListKnowledgeItemsUseCase(
    UseCaseContract[KnowledgeItemListQuery, KnowledgeItemPage]
):
    """
    One page of the knowledge base of a business, the last changed first,
    optionally only one kind and only active or inactive items: a keyset
    page of the database (`updated_at`, `kind` and `is_active` lookups of
    migration 1122), whatever the size of the knowledge base. While a
    post-deploy data task that fills those columns is open, the page says
    it is still indexing (older items may be missing).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        data_task_registry: DataTaskRegistryContract,
        data_task_state_repo: DataTaskStateRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._data_tasks: DataTaskRegistryContract = data_task_registry
        self._data_task_states: DataTaskStateRepoContract = data_task_state_repo

    def run(self, input_data: KnowledgeItemListQuery) -> KnowledgeItemPage:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        language: LanguageTag = input_data.language or business.owner_language
        page_items, next_cursor = finish_page(
            self._knowledge_item_repo.page_by_business(
                business.id,
                read_slice(input_data.page),
                input_data.kind,
                input_data.is_active,
            ),
            input_data.page,
            sort_key=lambda item: int(item.updated_at),
            item_id=lambda item: str(item.id),
        )
        resources: list[ResourceDocument] = self._resource_repo.list_by_business(
            business.id
        )
        return KnowledgeItemPage(
            items=[
                to_item_details(item, business.currency_code, language, resources)
                for item in page_items
            ],
            next_cursor=next_cursor,
            is_indexing=read_list_indexing(
                self._data_tasks, self._data_task_states, IndexedList.KNOWLEDGE
            ),
        )

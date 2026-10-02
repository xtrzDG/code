from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemList,
    UpsertKnowledgeItemsCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.knowledge_items import (
    to_item_details,
    upsert_knowledge_items,
)


class UpsertKnowledgeItemsUseCase(
    UseCaseContract[UpsertKnowledgeItemsCommand, KnowledgeItemList]
):
    """
    Create or update many knowledge items at once (menu import, wizard offer).

    Items match by id, or by kind and title, so repeating the same batch does
    not create duplicates. The whole batch is validated first: one invalid
    item leaves the knowledge base unchanged.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpsertKnowledgeItemsCommand) -> KnowledgeItemList:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        saved_items: list[KnowledgeItemDocument] = upsert_knowledge_items(
            business=business,
            template=self._niche_template_registry.get(business.niche_key),
            existing_items=self._knowledge_item_repo.list_by_business(business.id),
            item_inputs=input_data.items,
            source=input_data.source,
            now=self._wall_clock.now_unix(),
        )
        for item in saved_items:
            self._knowledge_item_repo.save(item)

        language: LanguageTag = input_data.language or business.owner_language
        return KnowledgeItemList(
            items=[
                to_item_details(item, business.currency_code, language)
                for item in saved_items
            ]
        )

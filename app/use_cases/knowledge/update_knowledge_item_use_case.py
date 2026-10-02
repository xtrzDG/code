from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemDetails,
    UpdateKnowledgeItemCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.knowledge_item_views import to_item_details
from app.utilities.knowledge.knowledge_items import patch_knowledge_item


class UpdateKnowledgeItemUseCase(
    UseCaseContract[UpdateKnowledgeItemCommand, KnowledgeItemDetails]
):
    """
    Change a knowledge item, including switching it on or off (`is_active`).

    Inactive items stay in the cabinet, but the assistant no longer finds or
    quotes them. An item of another business is reported as missing.
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

    def run(self, input_data: UpdateKnowledgeItemCommand) -> KnowledgeItemDetails:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        existing: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
            business.id,
            input_data.item_id,
        )
        if existing is None:
            raise NotFoundError(f"Knowledge item {input_data.item_id} was not found.")

        updated: KnowledgeItemDocument = patch_knowledge_item(
            business=business,
            template=self._niche_template_registry.get(business.niche_key),
            existing=existing,
            patch=input_data.patch,
            now=self._wall_clock.now_unix(),
        )
        self._knowledge_item_repo.save(updated)
        return to_item_details(
            updated,
            business.currency_code,
            input_data.language or business.owner_language,
        )

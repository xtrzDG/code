from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemDetails,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.knowledge_items import (
    build_knowledge_item,
    to_item_details,
)


class CreateKnowledgeItemUseCase(
    UseCaseContract[CreateKnowledgeItemCommand, KnowledgeItemDetails]
):
    """
    Add a fact to the knowledge base (dish, service, room type, FAQ, rule).

    The kind must be one the niche uses, and a price must be in the business
    currency; the assistant can quote it after the next assembly.
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

    def run(self, input_data: CreateKnowledgeItemCommand) -> KnowledgeItemDetails:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        item: KnowledgeItemDocument = build_knowledge_item(
            business=business,
            template=self._niche_template_registry.get(business.niche_key),
            item_input=input_data.item,
            source=input_data.source,
            now=self._wall_clock.now_unix(),
        )
        self._knowledge_item_repo.save(item)
        return to_item_details(
            item,
            business.currency_code,
            input_data.language or business.owner_language,
        )

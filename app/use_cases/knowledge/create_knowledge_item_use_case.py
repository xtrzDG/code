from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemDetails,
)
from app.use_cases.knowledge.knowledge_item_saves import KnowledgeItemWrites
from app.utilities.knowledge.knowledge_item_views import to_item_details
from app.utilities.knowledge.knowledge_items import build_knowledge_item


class CreateKnowledgeItemUseCase(
    KnowledgeItemWrites,
    UseCaseContract[CreateKnowledgeItemCommand, KnowledgeItemDetails],
):
    """
    Add a fact to the knowledge base (dish, service, room type, FAQ, rule).

    The kind must be one the niche uses, and a price must be in the business
    currency; the assistant can quote it after the next assembly. Its
    performers must be resources of the business.
    """

    def run(self, input_data: CreateKnowledgeItemCommand) -> KnowledgeItemDetails:
        business: BusinessDocument = self._business(input_data.business_id)
        item: KnowledgeItemDocument = build_knowledge_item(
            business=business,
            template=self._niche_template_registry.get(business.niche_key),
            item_input=input_data.item,
            source=input_data.source,
            now=self._wall_clock.now_unix(),
        )
        resources: list[ResourceDocument] = self._save_checked(item)
        return to_item_details(
            item,
            business.currency_code,
            input_data.language or business.owner_language,
            resources,
        )

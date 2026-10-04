from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemDetails,
    UpdateKnowledgeItemCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.knowledge.performer_links import (
    check_item_performers,
    unlink_left_out_resources,
)
from app.utilities.knowledge.knowledge_item_views import to_item_details
from app.utilities.knowledge.knowledge_items import patch_knowledge_item


class UpdateKnowledgeItemUseCase(
    UseCaseContract[UpdateKnowledgeItemCommand, KnowledgeItemDetails]
):
    """
    Change a knowledge item, including switching it on or off (`is_active`).

    Inactive items stay in the cabinet, but the assistant no longer finds or
    quotes them. An item of another business is reported as missing. A new
    performer list is the whole truth: resources left out stop listing the
    item among their services (or as their room type).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
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

        now: Microseconds = self._wall_clock.now_unix()
        updated: KnowledgeItemDocument = patch_knowledge_item(
            business=business,
            template=self._niche_template_registry.get(business.niche_key),
            existing=existing,
            patch=input_data.patch,
            now=now,
        )
        resources: list[ResourceDocument] = self._resource_repo.list_by_business(
            business.id
        )
        check_item_performers([updated], resources)
        self._knowledge_item_repo.save(updated)
        if input_data.patch.performer_resource_ids is not None:
            resources = unlink_left_out_resources(
                self._resource_repo, updated, resources, now
            )

        return to_item_details(
            updated,
            business.currency_code,
            input_data.language or business.owner_language,
            resources,
        )

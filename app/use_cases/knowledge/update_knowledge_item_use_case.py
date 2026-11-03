from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemDetails,
    UpdateKnowledgeItemCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.knowledge.knowledge_item_saves import KnowledgeItemWrites
from app.use_cases.knowledge.performer_links import unlink_left_out_resources
from app.utilities.knowledge.knowledge_item_patches import patch_knowledge_item
from app.utilities.knowledge.knowledge_item_views import to_item_details


class UpdateKnowledgeItemUseCase(
    KnowledgeItemWrites,
    UseCaseContract[UpdateKnowledgeItemCommand, KnowledgeItemDetails],
):
    """
    Change a knowledge item, including switching it on or off (`is_active`).

    Inactive items stay in the cabinet, but the assistant no longer finds or
    quotes them. An item of another business is reported as missing. A new
    performer list is the whole truth: resources left out stop listing the
    item among their services (or as their room type). The team member who
    changes it is kept as `updated_by` and the change is audited.
    """

    def run(self, input_data: UpdateKnowledgeItemCommand) -> KnowledgeItemDetails:
        business: BusinessDocument = self._business(input_data.business_id)
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
        ).model_copy(update={"updated_by": input_data.user_id})
        resources: list[ResourceDocument] = self._save_checked(
            updated, AuditAction.UPDATE
        )
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

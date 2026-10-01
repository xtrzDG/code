from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.use_cases.menu_import.imported_item_views import build_knowledge_item_view


class ConfirmImportedItemsUseCase(
    UseCaseContract[ConfirmImportedItemsCommand, ConfirmImportedItemsResult]
):
    """
    Activate the imported menu lines the owner checked, so the assistant may
    use them. Every id must be an imported item of this business; nothing is
    activated when one is not. Confirming an active item again is harmless.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        knowledge_item_repo: KnowledgeItemRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: ConfirmImportedItemsCommand
    ) -> ConfirmImportedItemsResult:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        if not input_data.item_ids:
            raise ValidationFailedError("Choose at least one imported item.")

        items: list[KnowledgeItemDocument] = []
        for item_id in dict.fromkeys(input_data.item_ids):
            item: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
                business.id, item_id
            )
            if item is None:
                raise NotFoundError(f"Knowledge item {item_id} was not found.")

            if item.source is not KnowledgeItemSource.MENU_IMPORT:
                raise ValidationFailedError(
                    f"Knowledge item {item_id} was not imported from a menu."
                )

            items.append(item)

        now: Microseconds = self._wall_clock.now_unix()
        for item in items:
            if not item.is_active:
                item.is_active = True
                item.updated_at = now
                self._knowledge_item_repo.save(item)

        return ConfirmImportedItemsResult(
            business_id=business.id,
            activated_items=[
                build_knowledge_item_view(item, business.owner_language)
                for item in items
            ],
        )

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.brands import BrandKnowledgeItemDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.brands.brand_knowledge import OverrideBrandKnowledgeCommand
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.utilities.brands.brand_knowledge_merge import location_copy
from app.utilities.knowledge.knowledge_item_views import to_item_details


class OverrideBrandKnowledgeUseCase(
    UseCaseContract[OverrideBrandKnowledgeCommand, KnowledgeItemDetails]
):
    """
    "Customise for this location": the location gets its own copy of one
    of its brand's shared facts, under the same shared key, to edit like
    any knowledge item; from the next assembly on the copy replaces the
    brand's item in this location only. Owners and staff of the location
    (a manager among them) may do it; ConflictError when the location
    already has its own item for the key.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._brand_items: BrandKnowledgeItemRepoContract = brand_knowledge_item_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OverrideBrandKnowledgeCommand) -> KnowledgeItemDetails:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        key = input_data.request.shared_key
        shared: BrandKnowledgeItemDocument | None = (
            None
            if business.brand_id is None
            else self._brand_items.get(business.brand_id, key)
        )
        if shared is None:
            raise NotFoundError("The brand of this business shares no such item.")

        if any(
            item.shared_key == key
            for item in self._knowledge_item_repo.list_by_business(business.id)
        ):
            raise ConflictError("This location already has its own item for it.")

        copy: KnowledgeItemDocument = location_copy(
            shared, business, self._wall_clock.now_unix()
        )
        self._knowledge_item_repo.save(copy)
        return to_item_details(copy, business.currency_code, business.owner_language)

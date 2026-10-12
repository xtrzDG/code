from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument, BrandKnowledgeItemDocument
from app.schemas.dto.brands.brand_commands import BrandAccessRequest
from app.schemas.dto.brands.brand_knowledge import (
    BrandKnowledgeItemCommand,
    BrandKnowledgeItemView,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.use_cases.brands.brand_knowledge_rules import (
    brand_currency,
    build_item,
    check_request,
    describe_item,
)


class UpdateBrandKnowledgeItemUseCase(
    UseCaseContract[BrandKnowledgeItemCommand, BrandKnowledgeItemView]
):
    """
    A brand owner changes a shared fact (its key stays): every location
    without its own item of that key gets the change at its next assembly.
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
        business_repo: BusinessRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._items: BrandKnowledgeItemRepoContract = brand_knowledge_item_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BrandKnowledgeItemCommand) -> BrandKnowledgeItemView:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        request = input_data.request
        if request is None:
            raise ValidationFailedError("Send the item's new content.")

        check_request(request)
        if request.shared_key not in (None, input_data.shared_key):
            raise ValidationFailedError("A shared item keeps its key.")

        currency = brand_currency(
            request.price_minor, self._business_repo.list_by_brand(brand.id)
        )
        now: Microseconds = self._wall_clock.now_unix()

        def change(stored: BrandKnowledgeItemDocument) -> BrandKnowledgeItemDocument:
            rebuilt: BrandKnowledgeItemDocument = build_item(
                brand.id,
                request.model_copy(update={"shared_key": stored.shared_key}),
                currency,
                now,
            )
            return rebuilt.model_copy(
                update={"id": stored.id, "created_at": stored.created_at}
            )

        updated: BrandKnowledgeItemDocument | None = self._items.modify(
            brand.id, input_data.shared_key, change
        )
        if updated is None:
            raise NotFoundError("The brand shares no item with this key.")

        return describe_item(updated, [])

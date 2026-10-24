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
    BrandKnowledgeCommand,
    BrandKnowledgeItemView,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.brands.brand_knowledge_rules import (
    brand_currency,
    build_item,
    check_request,
    describe_item,
)


class CreateBrandKnowledgeItemUseCase(
    UseCaseContract[BrandKnowledgeCommand, BrandKnowledgeItemView]
):
    """
    A brand owner adds a fact every location shares (from each location's
    next assembly on). Its shared key is unique in the brand: a second
    item with the same key is refused (ConflictError), in one step with
    what is stored.
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

    def run(self, input_data: BrandKnowledgeCommand) -> BrandKnowledgeItemView:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        request = input_data.request
        check_request(request)
        item: BrandKnowledgeItemDocument = build_item(
            brand.id,
            request,
            brand_currency(
                request.price_minor, self._business_repo.list_by_brand(brand.id)
            ),
            self._wall_clock.now_unix(),
        )
        if not self._items.add(item):
            raise ConflictError("The brand already shares an item with this key.")

        return describe_item(item, [])

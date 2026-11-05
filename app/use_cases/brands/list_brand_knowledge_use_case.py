from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.brands import BrandDocument
from app.schemas.dto.brands.brand_commands import BrandAccessRequest, BrandQuery
from app.schemas.dto.brands.brand_knowledge import BrandKnowledgeList
from app.use_cases.brands.brand_knowledge_rules import describe_item


class ListBrandKnowledgeUseCase(UseCaseContract[BrandQuery, BrandKnowledgeList]):
    """A brand's shared facts, oldest first, to a member of its team."""

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._items: BrandKnowledgeItemRepoContract = brand_knowledge_item_repo

    def run(self, input_data: BrandQuery) -> BrandKnowledgeList:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(user_id=input_data.user_id, brand_id=input_data.brand_id)
        )
        return BrandKnowledgeList(
            items=[
                describe_item(item, []) for item in self._items.list_by_brand(brand.id)
            ]
        )

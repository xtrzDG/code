from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.dto.brands.brand_commands import BrandAccessRequest
from app.schemas.dto.brands.brand_knowledge import BrandKnowledgeItemCommand
from app.schemas.exceptions.application_errors import NotFoundError


class DeleteBrandKnowledgeItemUseCase(UseCaseContract[BrandKnowledgeItemCommand, None]):
    """
    A brand owner stops sharing a fact (from each location's next assembly
    on); a location's own item with its key stays that location's.
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._items: BrandKnowledgeItemRepoContract = brand_knowledge_item_repo

    def run(self, input_data: BrandKnowledgeItemCommand) -> None:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        if self._items.get(brand.id, input_data.shared_key) is None:
            raise NotFoundError("The brand shares no item with this key.")

        self._items.delete(brand.id, input_data.shared_key)

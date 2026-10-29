from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
    BrandRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    DeleteBrandCommand,
)
from app.schemas.exceptions.application_errors import ConflictError


class DeleteBrandUseCase(UseCaseContract[DeleteBrandCommand, None]):
    """
    A brand owner removes a brand that has no location left, with the
    knowledge its locations shared (ConflictError while a location stays).
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_repo: BrandRepoContract,
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
        business_repo: BusinessRepoContract,
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._brand_repo: BrandRepoContract = brand_repo
        self._brand_knowledge_item_repo: BrandKnowledgeItemRepoContract = (
            brand_knowledge_item_repo
        )
        self._business_repo: BusinessRepoContract = business_repo

    def run(self, input_data: DeleteBrandCommand) -> None:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        if self._business_repo.list_by_brand(brand.id):
            raise ConflictError("Take every location out of the brand first.")

        for item in self._brand_knowledge_item_repo.list_by_brand(brand.id):
            self._brand_knowledge_item_repo.delete(brand.id, item.shared_key)

        self._brand_repo.delete(brand.id)

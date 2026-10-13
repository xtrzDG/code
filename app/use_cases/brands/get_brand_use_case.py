from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.brands import BrandDocument
from app.schemas.dto.brands.brand_commands import BrandAccessRequest, BrandQuery
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.use_cases.brands.brand_view_loading import BrandViewLoader


class GetBrandUseCase(UseCaseContract[BrandQuery, BrandView]):
    """One brand to a member of its team (others: 404), as they see it."""

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._views: BrandViewLoader = BrandViewLoader(
            business_repo, user_repo, brand_view_transformer
        )

    def run(self, input_data: BrandQuery) -> BrandView:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(user_id=input_data.user_id, brand_id=input_data.brand_id)
        )
        return self._views.load(brand, input_data.user_id)

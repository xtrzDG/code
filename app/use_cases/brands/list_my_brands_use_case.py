from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.brands.brand_view_loading import BrandViewLoader


class ListMyBrandsUseCase(UseCaseContract[UserId, list[BrandView]]):
    """The brands the person is on the team of, oldest first, as they see them."""

    def __init__(
        self,
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
    ) -> None:
        self._brand_repo: BrandRepoContract = brand_repo
        self._views: BrandViewLoader = BrandViewLoader(
            business_repo, user_repo, brand_view_transformer
        )

    def run(self, input_data: UserId) -> list[BrandView]:
        brands = sorted(
            self._brand_repo.list_by_member(input_data),
            key=lambda brand: brand.created_at,
        )
        return [self._views.load(brand, input_data) for brand in brands]

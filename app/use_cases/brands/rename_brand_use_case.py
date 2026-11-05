from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    RenameBrandCommand,
)
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.use_cases.brands.brand_rules import require_valid_brand_name
from app.use_cases.brands.brand_view_loading import BrandViewLoader


class RenameBrandUseCase(UseCaseContract[RenameBrandCommand, BrandView]):
    """A brand owner renames the brand."""

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._brand_repo: BrandRepoContract = brand_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._views: BrandViewLoader = BrandViewLoader(
            business_repo, user_repo, brand_view_transformer
        )

    def run(self, input_data: RenameBrandCommand) -> BrandView:
        self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        require_valid_brand_name(input_data.request.name)
        now: Microseconds = self._wall_clock.now_unix()

        def rename(current: BrandDocument) -> None:
            current.name = input_data.request.name
            current.updated_at = now

        brand: BrandDocument = self._brand_repo.update(input_data.brand_id, rename)
        return self._views.load(brand, input_data.user_id)

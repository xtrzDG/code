from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    CloneBrandLocationCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.businesses.business_settings_validation import (
    require_valid_business_name,
    require_valid_city_name,
)


class AuthorizeLocationCloneUseCase(
    UseCaseContract[CloneBrandLocationCommand, BusinessDocument]
):
    """
    "New location from…": a brand owner may make a new location from one
    of the brand's locations. Returns that location (the source);
    NotFoundError for a business that is no location of the brand.
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        business_repo: BusinessRepoContract,
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._business_repo: BusinessRepoContract = business_repo

    def run(self, input_data: CloneBrandLocationCommand) -> BusinessDocument:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        request = input_data.request
        require_valid_business_name(request.name)
        if request.city is not None:
            require_valid_city_name(request.city)

        source: BusinessDocument | None = self._business_repo.get(
            request.source_business_id
        )
        if source is None or source.brand_id != brand.id:
            raise NotFoundError("The brand has no such location.")

        return source

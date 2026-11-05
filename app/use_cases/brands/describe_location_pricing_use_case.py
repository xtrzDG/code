from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.brands.location_plans import LocationPlanQuery, LocationPricing
from app.use_cases.shared.brand_billing import (
    is_additional_location,
    is_setup_fee_covered,
)


class DescribeLocationPricingUseCase(
    UseCaseContract[LocationPlanQuery, LocationPricing]
):
    """
    How a business pays for a plan, for its billing page (owners only, as
    billing is): its country and texts' language (the owner's language
    unless asked otherwise), whether it is a further location of its brand
    and whether another location carries the brand's setup fee. Read as
    stored now, like the subscription prices (`app/use_cases/shared/
    brand_billing.py`), so the price the page quotes is the price billed.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._brand_repo: BrandRepoContract = brand_repo
        self._business_repo: BusinessRepoContract = business_repo

    def run(self, input_data: LocationPlanQuery) -> LocationPricing:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return LocationPricing(
            business_id=business.id,
            country_code=business.country_code,
            display_language=input_data.display_language or business.owner_language,
            is_additional_location=is_additional_location(
                self._business_repo, business
            ),
            is_setup_fee_covered=is_setup_fee_covered(
                self._brand_repo, self._business_repo, business
            ),
        )

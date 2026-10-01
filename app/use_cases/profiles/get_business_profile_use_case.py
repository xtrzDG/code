from app.contracts.repositories import BusinessProfileRepoContract, BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.profiles import BusinessProfileQuery, BusinessProfileView
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.profile_views import to_profile_view


class GetBusinessProfileUseCase(
    UseCaseContract[BusinessProfileQuery, BusinessProfileView]
):
    """Return the business profile, or a blank one before the first save."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo

    def run(self, input_data: BusinessProfileQuery) -> BusinessProfileView:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        return to_profile_view(business, profile)

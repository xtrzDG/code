from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.dto.brands.brand_commands import BrandAccessRequest
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.use_cases.shared.team_two_factor import (
    BRAND_TWO_FACTOR_MESSAGE,
    is_one_factor_session,
    require_team_two_factors,
)
from app.utilities.brands.brand_access import find_brand_member


class AuthorizeBrandAccessUseCase(UseCaseContract[BrandAccessRequest, BrandDocument]):
    """
    Return the brand when the person is on its team.

    A brand the person is not on the team of is reported as missing, not
    forbidden, so brand ids cannot be probed; a regional manager asking for
    a brand owner's action gets AccessDeniedError. The brand is read at
    every call, so someone taken off the team is out at the next request.
    What a member may do in each location is decided there, by the
    business access check, every time a location's data is read.

    A brand owner's action (`required_role` BRAND_OWNER: the shared
    answers every location's assistant reads, the team that reaches the
    locations, the locations themselves, the name) is an owner's action in
    every location of the brand. So when any location requires two
    factors of its team (`require_mfa_for_members`), a session signed in
    with the login code alone gets MfaRequiredError (reason
    `mfa_required`), as it would in that location itself. Work in the
    background (no session bound) acts on what a request authorized.
    """

    def __init__(
        self,
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        session_assurance: SessionAssuranceContract,
    ) -> None:
        self._brand_repo: BrandRepoContract = brand_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._session_assurance: SessionAssuranceContract = session_assurance

    def run(self, input_data: BrandAccessRequest) -> BrandDocument:
        brand: BrandDocument | None = self._brand_repo.get(input_data.brand_id)
        member: BrandMember | None = (
            None if brand is None else find_brand_member(brand, input_data.user_id)
        )
        if brand is None or member is None:
            raise NotFoundError(f"Brand {input_data.brand_id} was not found.")

        if input_data.required_role is not BrandMemberRole.BRAND_OWNER:
            return brand

        if member.role is not BrandMemberRole.BRAND_OWNER:
            raise AccessDeniedError("Only an owner of the brand may do this.")

        assurance: SessionAssurance | None = self._session_assurance.current()
        if is_one_factor_session(assurance, input_data.user_id):
            require_team_two_factors(
                assurance,
                input_data.user_id,
                self._business_repo.list_by_brand(brand.id),
                BRAND_TWO_FACTOR_MESSAGE,
            )

        return brand

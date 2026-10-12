from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.dto.brands.brand_commands import BrandAccessRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
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
    """

    def __init__(self, brand_repo: BrandRepoContract) -> None:
        self._brand_repo: BrandRepoContract = brand_repo

    def run(self, input_data: BrandAccessRequest) -> BrandDocument:
        brand: BrandDocument | None = self._brand_repo.get(input_data.brand_id)
        member: BrandMember | None = (
            None if brand is None else find_brand_member(brand, input_data.user_id)
        )
        if brand is None or member is None:
            raise NotFoundError(f"Brand {input_data.brand_id} was not found.")

        if (
            input_data.required_role is BrandMemberRole.BRAND_OWNER
            and member.role is not BrandMemberRole.BRAND_OWNER
        ):
            raise AccessDeniedError("Only an owner of the brand may do this.")

        return brand

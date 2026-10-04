from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.support_access import SupportAccessCheck
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.utilities.security.two_factor_policy import (
    is_two_factor_session,
    mfa_required,
)

TEAM_TWO_FACTOR_MESSAGE: str = (
    "This business asks its team to sign in with two factors: set up an "
    "authenticator app (Account → Security) and sign in again."
)


class AuthorizeBusinessAccessUseCase(
    UseCaseContract[BusinessAccessRequest, BusinessDocument]
):
    """
    Return the business when the user may act on it.

    A business the user is not a member of is reported as missing, not
    forbidden, so foreign ids cannot be probed. Staff asking for an
    owner-only action get AccessDeniedError. When the owner requires two
    factors of the team (`require_mfa_for_members`), a member's session
    signed in with the login code alone gets MfaRequiredError (reason
    `mfa_required`).

    Someone who is not a member may still be platform support with an
    open, time-boxed look into this cabinet: AuthorizeSupportAccessUseCase
    decides (admin role and two factors read at every call, read-only
    unless the owner allowed changes; concept sections 8 and 10).
    `access_mode` WRITE marks a read that copies personal data out (an
    export): support may do it only with the owner's consent.

    The two-factor rules apply to requests made with a session (the HTTP
    gateway binds it); work in the background (no session bound) acts on
    what such a request already authorized.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        session_assurance: SessionAssuranceContract,
        authorize_support_access: UseCaseContract[
            SupportAccessCheck, SupportAccessGrantDocument
        ],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._authorize_support_access: UseCaseContract[
            SupportAccessCheck, SupportAccessGrantDocument
        ] = authorize_support_access

    def run(self, input_data: BusinessAccessRequest) -> BusinessDocument:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        assurance: SessionAssurance | None = self._session_assurance.current()
        for member in business.members:
            if member.user_id != input_data.user_id:
                continue

            if (
                business.require_mfa_for_members
                and assurance is not None
                and not is_two_factor_session(assurance, input_data.user_id)
            ):
                raise mfa_required(TEAM_TWO_FACTOR_MESSAGE)

            if (
                input_data.required_role is BusinessMemberRole.OWNER
                and member.role is not BusinessMemberRole.OWNER
            ):
                raise AccessDeniedError("Only the business owner may do this.")

            return business

        self._authorize_support_access.run(
            SupportAccessCheck(
                user_id=input_data.user_id,
                business_id=business.id,
                required_role=input_data.required_role,
                access_mode=input_data.access_mode,
            )
        )
        return business

from app.contracts.platform_admins import (
    PlatformAdminRegistryContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.utilities.security.admin_permissions import has_permission
from app.utilities.security.two_factor_policy import (
    is_two_factor_session,
    mfa_required,
)

ADMINS_ONLY_MESSAGE: str = "Only platform admins may open the admin pages."
ROLE_MESSAGE: str = "Your platform admin role does not include this."
TWO_FACTOR_MESSAGE: str = (
    "The admin pages need a sign-in with two factors: set up an "
    "authenticator app and sign in again."
)


class AuthorizePlatformAdminUseCase(
    UseCaseContract[PlatformAdminAccessRequest, UserDocument]
):
    """
    Return the user when they are a platform admin whose role holds the
    permission the page or action needs (concept /admin; roles and
    permissions: `admin_permissions.py`).

    The role is read from the admin team at every call
    (PlatformAdminRegistryContract), so someone removed or given another
    role is refused at their next request; owning or working for a
    business never grants admin pages. The request's session must be
    signed in with two factors (MfaRequiredError, reason `mfa_required`,
    otherwise); a role without the permission gets AccessDeniedError.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        session_assurance: SessionAssuranceContract,
        platform_admins: PlatformAdminRegistryContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._platform_admins: PlatformAdminRegistryContract = platform_admins

    def run(self, input_data: PlatformAdminAccessRequest) -> UserDocument:
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        role: PlatformAdminRole | None = (
            None if user is None else self._platform_admins.role_of(user)
        )
        if user is None or role is None:
            raise AccessDeniedError(ADMINS_ONLY_MESSAGE)

        if not is_two_factor_session(self._session_assurance.current(), user.id):
            raise mfa_required(TWO_FACTOR_MESSAGE)

        if not has_permission(role, input_data.permission):
            raise AccessDeniedError(ROLE_MESSAGE)

        return user

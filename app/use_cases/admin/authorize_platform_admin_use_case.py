from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.platform_admins import is_listed_platform_admin
from app.utilities.security.two_factor_policy import (
    is_two_factor_session,
    mfa_required,
)

ADMINS_ONLY_MESSAGE: str = "Only platform admins may open the admin pages."
TWO_FACTOR_MESSAGE: str = (
    "The admin pages need a sign-in with two factors: set up an "
    "authenticator app and sign in again."
)


class AuthorizePlatformAdminUseCase(UseCaseContract[UserId, UserDocument]):
    """
    Return the user when they are a platform admin (concept /admin).

    Admin status is read from the PLATFORM_ADMIN_* lists at every call, so
    someone taken off them is refused at their next request; owning or
    working for a business never grants admin pages. The request's session
    must be signed in with two factors (MfaRequiredError, reason
    `mfa_required`, otherwise).
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        session_assurance: SessionAssuranceContract,
        app_settings: AppSettings,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: UserId) -> UserDocument:
        user: UserDocument | None = self._user_repo.get(input_data)
        if user is None or not is_listed_platform_admin(user, self._app_settings):
            raise AccessDeniedError(ADMINS_ONLY_MESSAGE)

        if not is_two_factor_session(self._session_assurance.current(), user.id):
            raise mfa_required(TWO_FACTOR_MESSAGE)

        return user

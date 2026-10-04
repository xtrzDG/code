"""
Shared pieces of tests that check access: the settings that name the
platform admins, and signed-in sessions as the HTTP gateway binds them.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

# The one platform admin of tests: users with this e-mail pass as one.
PLATFORM_ADMIN_EMAIL: str = "platform-admin@example.com"
ACCESS_SETTINGS: AppSettings = assemble_app_settings(
    {"PLATFORM_ADMIN_EMAILS": PLATFORM_ADMIN_EMAIL}
)


def settings_with_admins(
    emails: Sequence[str] = (), phone_numbers: Sequence[str] = ()
) -> AppSettings:
    """Settings whose PLATFORM_ADMIN_* lists name these people."""

    return assemble_app_settings(
        {
            "PLATFORM_ADMIN_EMAILS": ",".join(emails),
            "PLATFORM_ADMIN_PHONE_NUMBERS": ",".join(phone_numbers),
        }
    )


def platform_admin(locale: str = "en") -> UserDocument:
    """A verified platform admin on the ACCESS_SETTINGS list (stored flag set)."""

    return UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress(PLATFORM_ADMIN_EMAIL),
        locale=LanguageTag(locale),
        is_verified=True,
        is_platform_admin=True,
    )


def signed_in(
    user_id: UserId,
    auth_level: AuthLevel = AuthLevel.TWO_FACTOR,
    authenticated_at: int | None = None,
) -> SessionAssurance:
    """A session as the gateway binds it for a request of this user."""

    return SessionAssurance(
        user_id=user_id,
        session_id=UserSessionId(),
        auth_level=auth_level,
        authenticated_at=None
        if authenticated_at is None
        else Microseconds(authenticated_at),
    )


class AllowStepUp(StepUpGuardContract):
    """
    The step-up check of tests about something else: every action counts
    as recently confirmed (tests/users/mfa check the real one).
    """

    def require_recent_authentication(self) -> None:
        return None


class AuthorizeFlaggedAdmin(UseCaseContract[PlatformAdminAccessRequest, UserDocument]):
    """
    The admin check of tests about the admin pages' content: the stored
    flag decides, whatever the permission. tests/users/mfa and
    tests/users/access check the real one (roles from the admin team at
    every call and a session signed in with two factors).
    """

    def __init__(self, user_repo: UserRepoContract) -> None:
        self._user_repo: UserRepoContract = user_repo

    def run(self, input_data: PlatformAdminAccessRequest) -> UserDocument:
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is None or not user.is_platform_admin:
            raise AccessDeniedError("Only platform admins may open the admin pages.")
        return user

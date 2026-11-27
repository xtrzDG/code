"""
Platform admins on passkeys (ADMIN_PASSKEY_REQUIRED, on in production):
an admin who has a passkey answers a sign-in's second step with it, never
with the authenticator app's code (which a fake site can relay), and an
admin without a second factor sets up a passkey, not the app. A recovery
code stays the way back in after a lost passkey, and after a passkey
suspended as a possible copy (which still counts as having one). An admin
who has only the app still signs in with it, to add a passkey in Account →
Security; the admin pages stay closed until then
(AuthorizePlatformAdminUseCase). The second step offers the app's code
exactly where the API takes it (`is_app_code_refused`).

The person's admin flag is the one the login code step just stored.
"""

from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import UserDocument
from app.schemas.typings.mfa.constrained_strings import TotpCode
from app.schemas.typings.passkeys.booleans import IsAdminPasskeyRequired
from app.utilities.security.two_factor_policy import passkey_required

ADMIN_USES_PASSKEY_MESSAGE: str = (
    "Platform admins sign in with their passkey here; use the passkey, or "
    "a recovery code if it is lost."
)
ADMIN_ENROLS_PASSKEY_MESSAGE: str = (
    "Platform admins protect their account with a passkey: set up a passkey "
    "to finish signing in."
)


def is_admin_held_to_passkeys(settings: AppSettings, user: UserDocument) -> bool:
    return bool(settings.sessions.is_admin_passkey_required and user.is_platform_admin)


def is_app_code_refused(
    is_admin_passkey_required: IsAdminPasskeyRequired,
    passkey_repo: PasskeyRepoContract,
    user: UserDocument,
) -> bool:
    """
    The app's code never answers this person's sign-in: an admin held to
    passkeys who has one, whether or not it can sign (one suspended as a
    possible copy counts, and so does any while this server offers no
    passkeys). The second step leaves the app out for them
    (SecondStepOffer), and the API refuses its code (refuse_admin_app_code).
    """

    return bool(
        is_admin_passkey_required
        and user.is_platform_admin
        and int(passkey_repo.count_for_user(user.id)) > 0
    )


def refuse_admin_app_code(
    settings: AppSettings,
    passkey_repo: PasskeyRepoContract,
    user: UserDocument,
    code: TotpCode | None,
) -> None:
    """
    Raises:
        MfaRequiredError: (403 `passkey_required`) an admin with a passkey
            answered with the app's code.
    """

    if code is not None and is_app_code_refused(
        settings.sessions.is_admin_passkey_required, passkey_repo, user
    ):
        raise passkey_required(ADMIN_USES_PASSKEY_MESSAGE)


def refuse_admin_app_enrollment(settings: AppSettings, user: UserDocument) -> None:
    """
    Raises:
        MfaRequiredError: (403 `passkey_required`) an admin set up the app
            as their first second factor.
    """

    if is_admin_held_to_passkeys(settings, user):
        raise passkey_required(ADMIN_ENROLS_PASSKEY_MESSAGE)

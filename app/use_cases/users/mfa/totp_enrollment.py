"""Starting a new authenticator: a sealed secret and what the app needs."""

from typed_time_provider import Microseconds

from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import TotpEnrollmentView
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.mfa.constrained_strings import TotpSecret
from app.schemas.typings.mfa.strings import TotpAccountLabel
from app.utilities.security.totp_codes import (
    generate_totp_secret,
    totp_provisioning_uri,
)

ALREADY_ACTIVE_MESSAGE: str = (
    "An authenticator is already set up. Remove it first to set up another one."
)


def begin_totp_enrollment(
    totp_factor_repo: TotpFactorRepoContract,
    totp_secret_cipher: TotpSecretCipherAdapterContract,
    app_settings: AppSettings,
    user: UserDocument,
    now: Microseconds,
) -> TotpEnrollmentView:
    """
    A new PENDING authenticator (replacing one not confirmed yet), shown
    once: the QR code's address and the secret for typing it in.

    Raises:
        ConflictError: the user's authenticator is already on.
    """

    secret: TotpSecret = generate_totp_secret()
    factor = TotpFactorDocument(
        user_id=user.id,
        sealed_secret=totp_secret_cipher.seal(secret),
        created_at=now,
        updated_at=now,
    )
    if not totp_factor_repo.start_enrollment(factor):
        raise ConflictError(ALREADY_ACTIVE_MESSAGE)

    account_label: TotpAccountLabel = TotpAccountLabel(
        str(user.email or user.phone_number or user.id)
    )
    return TotpEnrollmentView(
        secret=secret,
        provisioning_uri=totp_provisioning_uri(
            secret, account_label, app_settings.mfa_issuer_name
        ),
        account_label=account_label,
        issuer=app_settings.mfa_issuer_name,
    )

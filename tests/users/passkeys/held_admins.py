"""
Platform admins held to passkeys in the admin passkey tests: the admin's
id, and an authenticator app that is on (set up before passkeys were
required), written straight to storage.
"""

from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.typings.mfa.constrained_integers import TotpTimeStep
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.totp_codes import generate_totp_secret
from tests.e2e.harness import Workshop
from tests.e2e.harness_settings import ADMIN_EMAIL


def give_app(workshop: Workshop, user_id: str) -> None:
    """An authenticator app that is on (set up before passkeys were required)."""

    secret = generate_totp_secret()
    workshop.authenticators.secrets[ADMIN_EMAIL] = secret
    now = workshop.clock.wall_clock.now_unix()
    factors = workshop.container.repositories.totp_factor_repo()
    assert factors.start_enrollment(
        TotpFactorDocument(
            user_id=UserId(user_id),
            sealed_secret=workshop.container.adapters.totp_secret_cipher().seal(secret),
            created_at=now,
            updated_at=now,
        )
    )
    assert factors.activate(UserId(user_id), TotpTimeStep(1), now) is not None


def admin_id(workshop: Workshop) -> str:
    users = workshop.container.repositories.user_repo()
    admin = users.find_by_email(EmailAddress(ADMIN_EMAIL))
    assert admin is not None
    return str(admin.id)

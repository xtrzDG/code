from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.passkeys.booleans import IsAdminPasskeyRequired
from app.schemas.typings.passkeys.constrained_strings import WebAuthnRelyingPartyId
from app.schemas.typings.platform.strings import LocalFilePath
from app.schemas.typings.users.constrained_integers import (
    SessionIdleTimeoutSeconds,
    SessionLifetimeSeconds,
)

DEFAULT_SESSION_IDLE_TIMEOUT_SECONDS: int = 7 * 24 * 60 * 60
DEFAULT_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS: int = 15 * 60
DEFAULT_ADMIN_SESSION_LIFETIME_SECONDS: int = 24 * 60 * 60


class SessionSettings(ImmutableDTO):
    """
    How long a session lives without use: a week for owners and staff
    (SESSION_IDLE_TIMEOUT_SECONDS), fifteen minutes for platform admins
    (ADMIN_SESSION_IDLE_TIMEOUT_SECONDS: the admin console); and at most,
    whatever its use, a day for platform admins
    (ADMIN_SESSION_LIFETIME_SECONDS; everyone else:
    SESSION_LIFETIME_SECONDS, 30 days).

    `is_admin_passkey_required` (ADMIN_PASSKEY_REQUIRED; on by default in
    production, which refuses to start with it off): platform admins prove
    it is them with a passkey (phishing resistant), never with the
    authenticator app's code alone.

    Passkeys are bound to `webauthn_rp_id` (WEBAUTHN_RP_ID; by default the
    host of CABINET_BASE_URL; None: no passkeys), and the device list shows
    an approximate country next to an address from the offline GeoLite2
    country database at `geoip_country_database_path`
    (GEOIP_COUNTRY_DATABASE_PATH; None: no countries).
    """

    idle_timeout_seconds: SessionIdleTimeoutSeconds = SessionIdleTimeoutSeconds(
        DEFAULT_SESSION_IDLE_TIMEOUT_SECONDS
    )
    admin_idle_timeout_seconds: SessionIdleTimeoutSeconds = SessionIdleTimeoutSeconds(
        DEFAULT_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS
    )
    admin_lifetime_seconds: SessionLifetimeSeconds = SessionLifetimeSeconds(
        DEFAULT_ADMIN_SESSION_LIFETIME_SECONDS
    )
    webauthn_rp_id: WebAuthnRelyingPartyId | None = None
    geoip_country_database_path: LocalFilePath | None = None
    is_admin_passkey_required: IsAdminPasskeyRequired = False

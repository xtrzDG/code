from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.booleans import (
    IsOtpChallengeConsumed,
    IsPlatformAdmin,
    IsUserVerified,
    IsVerifiedLoginDestination,
)
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.constrained_strings import (
    EmailAddress,
    SessionUserAgent,
)
from app.schemas.typings.users.prefixed_id import (
    OtpChallengeId,
    UserId,
    UserSessionId,
)
from app.schemas.typings.users.strings import (
    AccessTokenHash,
    OtpCodeHash,
    UserDisplayName,
)


class UserDocument(BaseDocument):
    """
    A person who signs in: owner or staff of businesses, or the platform admin.

    Signs in with a phone number of any country or with e-mail. Roles inside a
    business live on the business (members); `is_platform_admin` is global.
    `signup_attribution` is where they came from, set once when the account
    is created (the founder's acquisition reports).
    """

    # 2: `signup_attribution` (optional, so version 1 needs no upcaster).
    schema_version: SchemaVersion = SchemaVersion("2")
    id: UserId = Field(default_factory=UserId)
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    country_code: CountryCode | None = None
    locale: LanguageTag
    display_name: UserDisplayName | None = None
    is_verified: IsUserVerified = False
    is_platform_admin: IsPlatformAdmin = False
    signup_attribution: SignupAttribution | None = None


class OtpChallengeDocument(BaseDocument):
    """
    One login attempt with a one-time code; only the code hash is stored.
    `is_verified_destination` marks a code for a verified user's phone or
    e-mail: those sends count against a budget of their own.
    """

    # 2: `is_verified_destination` (optional, so version 1 needs no upcaster).
    schema_version: SchemaVersion = SchemaVersion("2")
    id: OtpChallengeId = Field(default_factory=OtpChallengeId)
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    country_code: CountryCode | None = None
    delivery_channel: OtpDeliveryChannel
    locale: LanguageTag
    code_hash: OtpCodeHash
    expires_at: Microseconds
    failed_attempts: OtpAttemptCount = OtpAttemptCount(0)
    is_consumed: IsOtpChallengeConsumed = False
    requested_from_ip: ClientIpAddress | None = None
    is_verified_destination: IsVerifiedLoginDestination = False


class UserSessionDocument(BaseDocument):
    """
    Signed-in session; only the SHA-256 hash of the bearer token is stored.

    `auth_level` says how it was signed in (the login code alone, or with
    an authenticator or recovery code too) and `authenticated_at` when the
    person last proved it is them: at sign-in, and again when they confirm
    a sensitive action (step-up). A session of version 1 has neither and
    counts as one factor that must confirm its next sensitive action.

    The device: the User-Agent it was signed in with (`user_agent`, the
    latest one when it changes) and the address it was opened from
    (`created_ip`). `last_seen_at` and `last_seen_ip` follow its use, at
    most every five minutes; each such write also slides `idle_expires_at`
    (a session unused that long ends: a week for owners and staff, twelve
    hours for platform admins). `expires_at` is the absolute end (30 days,
    a day for platform admins). Sessions from before version 3 have none
    of these and get them at their next use.
    """

    # 2: `auth_level` and `authenticated_at`; 3: the device, its last use
    # and the idle expiry (all optional, so older versions need no upcaster).
    schema_version: SchemaVersion = SchemaVersion("3")
    id: UserSessionId = Field(default_factory=UserSessionId)
    user_id: UserId
    token_hash: AccessTokenHash
    expires_at: Microseconds
    auth_level: AuthLevel | None = None
    authenticated_at: Microseconds | None = None
    user_agent: SessionUserAgent | None = None
    created_ip: ClientIpAddress | None = None
    last_seen_at: Microseconds | None = None
    last_seen_ip: ClientIpAddress | None = None
    idle_expires_at: Microseconds | None = None

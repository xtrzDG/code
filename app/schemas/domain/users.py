from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginMethod
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
)
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.constrained_strings import EmailAddress
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
    """

    id: UserId = Field(default_factory=UserId)
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    country_code: CountryCode | None = None
    locale: LanguageTag
    display_name: UserDisplayName | None = None
    is_verified: IsUserVerified = False
    is_platform_admin: IsPlatformAdmin = False


class OtpChallengeDocument(BaseDocument):
    """One login attempt with a one-time code; only the code hash is stored."""

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


class UserSessionDocument(BaseDocument):
    """Signed-in session; only the SHA-256 hash of the bearer token is stored."""

    id: UserSessionId = Field(default_factory=UserSessionId)
    user_id: UserId
    token_hash: AccessTokenHash
    expires_at: Microseconds

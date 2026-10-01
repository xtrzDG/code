from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.accounts import LoginMethod
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.typings.accounts.booleans import (
    IsOtpChallengeConsumed,
    IsOwnerVerified,
)
from app.schemas.typings.accounts.constrained_integers import OtpAttemptCount
from app.schemas.typings.accounts.constrained_strings import EmailAddress
from app.schemas.typings.accounts.prefixed_id import (
    OtpChallengeId,
    OwnerId,
    OwnerSessionId,
)
from app.schemas.typings.accounts.strings import (
    AccessTokenHash,
    OtpCodeHash,
    OwnerDisplayName,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)


class OwnerDocument(BaseDocument):
    """Business owner account. Signs in with a phone of any country or e-mail."""

    id: OwnerId = Field(default_factory=OwnerId)
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    country_code: CountryCode | None = None
    preferred_language: LanguageTag
    display_name: OwnerDisplayName | None = None
    is_verified: IsOwnerVerified = False


class OtpChallengeDocument(BaseDocument):
    """One login attempt with a one-time code; only the code hash is stored."""

    id: OtpChallengeId = Field(default_factory=OtpChallengeId)
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    country_code: CountryCode | None = None
    delivery_channel: OtpDeliveryChannel
    preferred_language: LanguageTag
    code_hash: OtpCodeHash
    expires_at: Microseconds
    failed_attempts: OtpAttemptCount = OtpAttemptCount(0)
    is_consumed: IsOtpChallengeConsumed = False


class OwnerSessionDocument(BaseDocument):
    """Owner session; only the SHA-256 hash of the bearer token is stored."""

    id: OwnerSessionId = Field(default_factory=OwnerSessionId)
    owner_id: OwnerId
    token_hash: AccessTokenHash
    expires_at: Microseconds

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.dto.mfa_login import MfaChallengeView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.schemas.typings.mfa.booleans import IsMfaRequired
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.schemas.typings.users.booleans import (
    IsNewUser,
    IsPlatformAdmin,
    IsUserVerified,
)
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.schemas.typings.users.constrained_strings import (
    EmailAddress,
    OtpCode,
    TurnstileResponseToken,
)
from app.schemas.typings.users.prefixed_id import OtpChallengeId, UserId
from app.schemas.typings.users.strings import (
    AccessToken,
    MaskedLoginDestination,
    RawEmailAddressInput,
    UserDisplayName,
)


class StartOtpLoginRequest(ImmutableDTO):
    """
    Ask for a one-time login code by phone number or e-mail.

    Exactly one of `phone_number` (any country, any format) and `email` is
    set. `country_hint` is needed only for national phone formats without
    "+"; `locale` is the language of the code message and of a new account.
    `preferred_delivery_channel` is used when the phone's country allows it;
    asking for another channel right after a code was sent ("send by SMS
    instead") is allowed once per channel. `turnstile_token` is the answer
    of the Cloudflare Turnstile check, sent again after a 403 whose reason
    is `challenge_required` (its details hold the widget's site key).
    """

    phone_number: RawPhoneNumberInput | None = None
    email: RawEmailAddressInput | None = None
    country_hint: CountryCode | None = None
    locale: LanguageTag | None = None
    preferred_delivery_channel: OtpDeliveryChannel | None = None
    turnstile_token: TurnstileResponseToken | None = None


class StartOtpLoginCommand(ImmutableDTO):
    """A login code request with the caller's address (hourly limits)."""

    phone_number: RawPhoneNumberInput | None = None
    email: RawEmailAddressInput | None = None
    country_hint: CountryCode | None = None
    locale: LanguageTag | None = None
    preferred_delivery_channel: OtpDeliveryChannel | None = None
    turnstile_token: TurnstileResponseToken | None = None
    client_ip_address: ClientIpAddress | None = None


class OtpChallengeView(ImmutableDTO):
    """A sent login code: where it went and how long it stays valid."""

    challenge_id: OtpChallengeId
    login_method: LoginMethod
    delivery_channel: OtpDeliveryChannel
    masked_destination: MaskedLoginDestination
    expires_in_seconds: OtpLifetimeSeconds
    locale: LanguageTag
    phone_number: E164PhoneNumber | None = None
    international_phone_number: FormattedPhoneNumber | None = None
    country_code: CountryCode | None = None


class VerifyOtpLoginRequest(ImmutableDTO):
    """
    HTTP body of the code check; the cabinet adds where a new owner came
    from (its first-party attribution cookie), kept only for a new account.
    """

    challenge_id: OtpChallengeId
    code: OtpCode
    signup_attribution: SignupAttribution | None = None


class VerifyOtpLoginCommand(ImmutableDTO):
    """Check a login code and open a session."""

    challenge_id: OtpChallengeId
    code: OtpCode
    client_ip_address: ClientIpAddress | None = None
    signup_attribution: SignupAttribution | None = None


class UserView(ImmutableDTO):
    """A signed-in person as shown to themselves and to their team."""

    id: UserId
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    country_code: CountryCode | None = None
    locale: LanguageTag
    display_name: UserDisplayName | None = None
    is_verified: IsUserVerified
    is_platform_admin: IsPlatformAdmin


class LoginSessionView(ImmutableDTO):
    """
    A new session. The bearer token is shown only here; the server keeps
    nothing but its hash.

    When the person must also give an authenticator code (they set one up,
    or they are a platform admin), the login code step answers
    `mfa_required` with the `mfa_challenge` instead, and no token, expiry
    or user: `POST /v1/auth/mfa/verify` opens the session. A session opened
    while setting up the authenticator carries the new `recovery_codes`
    (shown once).
    """

    access_token: AccessToken | None = None
    expires_at: Microseconds | None = None
    user: UserView | None = None
    is_new_user: IsNewUser
    mfa_required: IsMfaRequired = False
    mfa_challenge: MfaChallengeView | None = None
    auth_level: AuthLevel | None = None
    recovery_codes: list[RecoveryCode] = Field(default_factory=list[RecoveryCode])


class LogoutCommand(ImmutableDTO):
    """End the session behind a bearer token."""

    access_token: AccessToken


class UserMembershipView(ImmutableDTO):
    """A business the user belongs to and the role there."""

    business_id: BusinessId
    business_name: BusinessName
    role: BusinessMemberRole
    business_status: BusinessStatus
    country_code: CountryCode


class CurrentUserView(ImmutableDTO):
    """
    The signed-in user and every business they work in, and how the current
    session is signed in (None outside a signed-in request).
    """

    user: UserView
    memberships: list[UserMembershipView] = Field(
        default_factory=list[UserMembershipView]
    )
    auth_level: AuthLevel | None = None


class UpdateCurrentUserRequest(ImmutableDTO):
    """
    HTTP body of a profile change.

    Missing fields stay unchanged; an empty `display_name` clears the name.
    """

    display_name: UserDisplayName | None = None
    locale: LanguageTag | None = None


class UpdateCurrentUserCommand(ImmutableDTO):
    """Change the signed-in user's name or interface language."""

    user_id: UserId
    display_name: UserDisplayName | None = None
    locale: LanguageTag | None = None

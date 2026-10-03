"""
Login abuse protection: who a login code would go to, the bot check of a
risky request, and the alert when a platform cap refuses sends.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginCodeCap, LoginMethod
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.booleans import (
    IsBotCheckPassed,
    IsVerifiedLoginDestination,
)
from app.schemas.typings.users.constrained_integers import OtpSendLimit
from app.schemas.typings.users.constrained_strings import (
    EmailAddress,
    TurnstileAction,
    TurnstileResponseToken,
)
from app.schemas.typings.users.strings import TurnstileErrorCode


class LoginCodeDestination(ImmutableDTO):
    """
    Where a login code would be sent and who asks for it: what the send
    limits and the risk signals of a code request look at.
    `is_verified_destination` is true when a verified user signs in with
    this phone or e-mail (their sends have a budget of their own).
    """

    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    country_code: CountryCode | None = None
    requested_channel: OtpDeliveryChannel | None = None
    client_ip_address: ClientIpAddress | None = None
    is_verified_destination: IsVerifiedLoginDestination


class SendLoginCodeCommand(ImmutableDTO):
    """
    Send a login code to a checked destination through the first of
    `delivery_channels` that works, in `locale`. `turnstile_token` is the
    passed bot check, when the client has one.
    """

    destination: LoginCodeDestination
    delivery_channels: list[OtpDeliveryChannel] = Field(min_length=1)
    locale: LanguageTag
    turnstile_token: TurnstileResponseToken | None = None


class TurnstileVerification(ImmutableDTO):
    """What Cloudflare's siteverify said about one Turnstile token."""

    is_passed: IsBotCheckPassed
    action: TurnstileAction | None = None
    error_codes: list[TurnstileErrorCode] = Field(
        default_factory=list[TurnstileErrorCode]
    )


class LoginCodeCapAlert(ImmutableDTO):
    """
    A platform cap of login code sends refused a send: the cap, its hourly
    limit and, for the per-country cap, the country.
    """

    cap: LoginCodeCap
    limit: OtpSendLimit
    country_code: CountryCode | None = None

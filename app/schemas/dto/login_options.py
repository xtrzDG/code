"""Which ways of signing in work right now, before a code is requested."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.typings.legal.constrained_strings import LegalDocumentVersion
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.booleans import (
    IsEmailLoginAvailable,
    IsPhoneLoginAvailable,
    IsSignUpRestricted,
)


class LoginOptionsQuery(ImmutableDTO):
    """Sign-in options, optionally for phone numbers of one country."""

    country_code: CountryCode | None = None


class LoginOptionsView(ImmutableDTO):
    """
    The login-code channels that work right now: the country's channels
    that have a configured provider (all configured phone channels when no
    country is given), in the order they are tried, and whether e-mail
    sign-in works. `is_sign_up_restricted` is true for a country whose
    numbers cannot sign in at all. `configured_channels` are all channels
    with a provider, for any country (empty: sign-in is down everywhere).
    """

    country_code: CountryCode | None = None
    phone_channels: list[OtpDeliveryChannel]
    configured_channels: list[OtpDeliveryChannel]
    is_phone_login_available: IsPhoneLoginAvailable
    is_email_login_available: IsEmailLoginAvailable
    is_sign_up_restricted: IsSignUpRestricted = False
    # The terms of service and privacy policy in force, which the code
    # step's acceptance line names (None before the first version).
    terms_version: LegalDocumentVersion | None = None
    privacy_version: LegalDocumentVersion | None = None

"""
OTP_*, TURNSTILE_* and SESSION_LIFETIME_SECONDS: login codes, their abuse
limits and bot check, and cabinet sessions.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    PhoneNumberPrefix,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.booleans import IsOtpCodeLoggingEnabled
from app.schemas.typings.users.constrained_integers import (
    OtpAttemptCount,
    OtpLifetimeSeconds,
    OtpSendLimit,
    OtpVerifyLimit,
    SessionLifetimeSeconds,
)
from app.schemas.typings.users.constrained_strings import TurnstileSiteKey
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_setting,
    optional_text,
    parse_setting,
    read_boolean,
    read_integer,
    read_list,
    read_raw_list,
)

# Destinations that SMS providers' fraud reports name often for SMS pumping
# (international revenue share fraud): small Pacific territories and some
# African networks with high termination rates. A code request for a phone
# there needs the bot check; set OTP_HIGH_RISK_COUNTRIES to replace the list
# (an empty value turns the signal off).
DEFAULT_OTP_HIGH_RISK_COUNTRIES: str = (
    "CF,CK,ER,GN,GW,KI,KM,LR,MR,NR,NU,PG,SB,SL,SO,ST,TD,TK,TL,TV,VU"
)


class LoginSettingsSection(TypedDict):
    """The `AppSettings` fields of login codes and sessions."""

    otp_lifetime_seconds: OtpLifetimeSeconds
    otp_max_failed_attempts: OtpAttemptCount
    otp_sends_per_destination_per_hour: OtpSendLimit
    otp_sends_per_ip_per_hour: OtpSendLimit
    otp_sends_per_hour: OtpSendLimit
    otp_sends_per_country_per_hour: OtpSendLimit
    otp_sends_to_verified_users_per_hour: OtpSendLimit
    otp_verifies_per_ip_per_10_minutes: OtpVerifyLimit
    otp_high_risk_country_codes: list[CountryCode]
    otp_denied_phone_prefixes: list[PhoneNumberPrefix]
    turnstile_site_key: TurnstileSiteKey | None
    turnstile_secret_key: PlatformSecret | None
    is_otp_code_logging_enabled: IsOtpCodeLoggingEnabled
    session_lifetime_seconds: SessionLifetimeSeconds


def read_otp_code_logging(
    environment_variables: Mapping[str, str],
    is_development: bool,
) -> bool:
    """
    OTP_LOG_CODES: on by default in development and tests.

    Raises:
        ValidationFailedError: enabled in production.
    """

    is_otp_code_logging_enabled: bool = read_boolean(
        environment_variables, "OTP_LOG_CODES", is_development
    )
    if is_otp_code_logging_enabled and not is_development:
        raise ValidationFailedError(
            "OTP_LOG_CODES cannot be enabled in production: login codes would be "
            "written to the log. Configure a login code provider instead."
        )

    return is_otp_code_logging_enabled


def read_login_settings(
    environment_variables: Mapping[str, str],
    is_otp_code_logging_enabled: bool,
) -> LoginSettingsSection:
    return LoginSettingsSection(
        otp_lifetime_seconds=OtpLifetimeSeconds(
            read_integer(environment_variables, "OTP_LIFETIME_SECONDS", 600)
        ),
        otp_max_failed_attempts=OtpAttemptCount(
            read_integer(environment_variables, "OTP_MAX_FAILED_ATTEMPTS", 5)
        ),
        otp_sends_per_destination_per_hour=OtpSendLimit(
            read_integer(environment_variables, "OTP_SENDS_PER_DESTINATION_PER_HOUR", 5)
        ),
        otp_sends_per_ip_per_hour=OtpSendLimit(
            read_integer(environment_variables, "OTP_SENDS_PER_IP_PER_HOUR", 10)
        ),
        otp_sends_per_hour=OtpSendLimit(
            read_integer(environment_variables, "OTP_SENDS_PER_HOUR", 300)
        ),
        otp_sends_per_country_per_hour=OtpSendLimit(
            read_integer(environment_variables, "OTP_SENDS_PER_COUNTRY_PER_HOUR", 100)
        ),
        otp_sends_to_verified_users_per_hour=OtpSendLimit(
            read_integer(
                environment_variables, "OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR", 300
            )
        ),
        otp_verifies_per_ip_per_10_minutes=OtpVerifyLimit(
            read_integer(
                environment_variables, "OTP_VERIFIES_PER_IP_PER_10_MINUTES", 20
            )
        ),
        otp_high_risk_country_codes=[
            parse_setting("OTP_HIGH_RISK_COUNTRIES", country_code, CountryCode)
            for country_code in read_list(
                environment_variables,
                "OTP_HIGH_RISK_COUNTRIES",
                DEFAULT_OTP_HIGH_RISK_COUNTRIES,
            )
        ],
        otp_denied_phone_prefixes=[
            parse_setting("OTP_DENIED_PHONE_PREFIXES", prefix, PhoneNumberPrefix)
            for prefix in read_raw_list(
                environment_variables, "OTP_DENIED_PHONE_PREFIXES"
            )
        ],
        **read_turnstile_keys(environment_variables),
        is_otp_code_logging_enabled=IsOtpCodeLoggingEnabled(
            is_otp_code_logging_enabled
        ),
        session_lifetime_seconds=SessionLifetimeSeconds(
            read_integer(
                environment_variables,
                "SESSION_LIFETIME_SECONDS",
                30 * 24 * 60 * 60,
            )
        ),
    )


class TurnstileKeys(TypedDict):
    turnstile_site_key: TurnstileSiteKey | None
    turnstile_secret_key: PlatformSecret | None


def read_turnstile_keys(environment_variables: Mapping[str, str]) -> TurnstileKeys:
    """
    TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY: both (the bot check is on)
    or neither (off: development, tests, or not set up yet).

    Raises:
        ValidationFailedError: only one of them is set.
    """

    site_key: TurnstileSiteKey | None = optional_setting(
        environment_variables, "TURNSTILE_SITE_KEY", TurnstileSiteKey
    )
    secret_key: PlatformSecret | None = optional_text(
        environment_variables, "TURNSTILE_SECRET_KEY", PlatformSecret
    )
    if (site_key is None) != (secret_key is None):
        raise ValidationFailedError(
            "Set both TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY to turn the "
            "bot check of login code requests on, or neither."
        )

    return TurnstileKeys(turnstile_site_key=site_key, turnstile_secret_key=secret_key)

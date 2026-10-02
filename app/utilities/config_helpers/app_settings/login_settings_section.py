"""OTP_* and SESSION_LIFETIME_SECONDS: login codes and cabinet sessions."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.users.booleans import IsOtpCodeLoggingEnabled
from app.schemas.typings.users.constrained_integers import (
    OtpAttemptCount,
    OtpLifetimeSeconds,
    OtpSendLimit,
    SessionLifetimeSeconds,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    read_boolean,
    read_integer,
)


class LoginSettingsSection(TypedDict):
    """The `AppSettings` fields of login codes and sessions."""

    otp_lifetime_seconds: OtpLifetimeSeconds
    otp_max_failed_attempts: OtpAttemptCount
    otp_sends_per_destination_per_hour: OtpSendLimit
    otp_sends_per_ip_per_hour: OtpSendLimit
    otp_sends_per_hour: OtpSendLimit
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

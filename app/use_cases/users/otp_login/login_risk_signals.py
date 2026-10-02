"""
When a login code request needs a bot check (Cloudflare Turnstile) before
the paid send, and the check itself.
"""

from collections.abc import Callable

from app.contracts.login_protection import BotCheckFacilitatorContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.users import LoginMethod, LoginRiskSignal
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.login_protection import LoginCodeDestination
from app.schemas.exceptions.login_errors import BotCheckRequiredError
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.constrained_strings import (
    TurnstileResponseToken,
    TurnstileSiteKey,
)
from app.use_cases.users.otp_login.login_code_limits import (
    find_budget_limit,
    list_same_budget,
)

# Codes one client address may ask for in an hour before every further
# request is checked (the hourly cap per address is higher).
QUIET_SENDS_PER_ADDRESS: int = 3
CHALLENGE_REQUIRED_REASON: ErrorReasonCode = ErrorReasonCode("challenge_required")
CHALLENGE_REQUIRED_MESSAGE: str = (
    "Confirm that you are not a robot, then ask for the code again."
)
CHALLENGE_FAILED_MESSAGE: str = (
    "The robot check was not passed or has expired. Try it again."
)


def find_login_risk_signals(
    recent: list[OtpChallengeDocument],
    destination: LoginCodeDestination,
    app_settings: AppSettings,
) -> list[LoginRiskSignal]:
    """
    Why this request is risky, given the challenges of the last hour: the
    phone or e-mail belongs to no verified user, the client address asked
    for 3 codes already, half of the platform budget is used, or the phone
    is in a country of OTP_HIGH_RISK_COUNTRIES. Empty for a returning
    owner on a quiet day.
    """

    signals: list[LoginRiskSignal] = []
    if not destination.is_verified_destination:
        signals.append(LoginRiskSignal.NEW_DESTINATION)

    if destination.client_ip_address is not None and (
        len(
            [
                challenge
                for challenge in recent
                if challenge.requested_from_ip == destination.client_ip_address
            ]
        )
        >= QUIET_SENDS_PER_ADDRESS
    ):
        signals.append(LoginRiskSignal.BUSY_CLIENT_ADDRESS)

    if 2 * len(list_same_budget(recent, destination)) >= int(
        find_budget_limit(destination, app_settings)
    ):
        signals.append(LoginRiskSignal.HIGH_PLATFORM_USAGE)

    if (
        destination.login_method is LoginMethod.PHONE
        and destination.country_code in app_settings.otp_high_risk_country_codes
    ):
        signals.append(LoginRiskSignal.HIGH_RISK_COUNTRY)

    return signals


def require_bot_check_when_risky(
    bot_check: BotCheckFacilitatorContract,
    list_recent: Callable[[], list[OtpChallengeDocument]],
    destination: LoginCodeDestination,
    token: TurnstileResponseToken | None,
    app_settings: AppSettings,
) -> None:
    """
    Let a request through when the bot check is off, the request shows no
    risk signal, or its token passes the check. `list_recent` (the
    challenges of the last hour) is read only while the check is on.

    Raises:
        BotCheckRequiredError: the check is needed and was not passed; its
            reason `challenge_required` names the widget's site key. The
            signals are not named, so the answer does not tell whether a
            phone or e-mail belongs to a user.
    """

    site_key: TurnstileSiteKey | None = bot_check.site_key()
    if site_key is None or not find_login_risk_signals(
        list_recent(), destination, app_settings
    ):
        return

    if token is None:
        raise build_challenge_required_error(site_key, CHALLENGE_REQUIRED_MESSAGE)

    if not bot_check.is_passed(token, destination.client_ip_address):
        raise build_challenge_required_error(site_key, CHALLENGE_FAILED_MESSAGE)


def build_challenge_required_error(
    site_key: TurnstileSiteKey,
    message: str,
) -> BotCheckRequiredError:
    return BotCheckRequiredError(
        message,
        reasons=[
            ErrorReason(
                code=CHALLENGE_REQUIRED_REASON,
                message=ErrorReasonMessage(message),
                details=[ErrorReasonDetail(str(site_key))],
            )
        ],
    )

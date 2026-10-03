"""
How often login codes may be sent: per destination, client address, country
and in total, with a separate total for verified users.
"""

from typed_time_provider import Microseconds, Seconds, WallClock

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.users import LoginCodeCap, LoginMethod
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.login_protection import LoginCodeCapAlert, LoginCodeDestination
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.exceptions.login_errors import LoginCodeCapReachedError
from app.schemas.typings.users.constrained_integers import OtpSendLimit

RESEND_INTERVAL_SECONDS: int = 30
LIMIT_WINDOW_SECONDS: int = 60 * 60
TOO_MANY_CODES_MESSAGE: str = "Too many login codes were requested. Try again later."


def refuse_over_login_code_limits(
    recent: list[OtpChallengeDocument],
    destination: LoginCodeDestination,
    wall_clock: WallClock[Microseconds],
    app_settings: AppSettings,
) -> None:
    """
    Refuse a send, given the challenges of the last hour (`recent`):
    within 30 seconds of the last one to the same destination and channel
    (a phone may switch to another channel at once), or over the hourly
    caps per destination and per client address, or over a platform cap.

    The platform caps keep two budgets: codes for verified users' phones
    and e-mails, and codes for everything else (new destinations), so a
    flood of codes to new numbers cannot lock returning owners out. Codes
    to new phone numbers are also capped per country (SMS pumping aims at
    the expensive networks of a few countries).

    Raises:
        RateLimitedError: a per-destination or per-address limit.
        LoginCodeCapReachedError: a platform cap (the team is alerted).
    """

    resend_start: int = int(
        wall_clock.now_unix_with_delta(Seconds(-RESEND_INTERVAL_SECONDS))
    )
    same_destination: list[OtpChallengeDocument] = [
        challenge for challenge in recent if is_same_destination(challenge, destination)
    ]
    if any(
        int(challenge.created_at) > resend_start
        and (
            destination.phone_number is None
            or destination.requested_channel is None
            or challenge.delivery_channel == destination.requested_channel
        )
        for challenge in same_destination
    ):
        raise RateLimitedError(
            f"A code was just sent. Wait {RESEND_INTERVAL_SECONDS} seconds "
            "before asking for another one."
        )

    if len(same_destination) >= int(app_settings.otp_sends_per_destination_per_hour):
        raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

    if destination.client_ip_address is not None and len(
        [
            challenge
            for challenge in recent
            if challenge.requested_from_ip == destination.client_ip_address
        ]
    ) >= int(app_settings.otp_sends_per_ip_per_hour):
        raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

    refuse_over_platform_caps(recent, destination, app_settings)


def refuse_over_platform_caps(
    recent: list[OtpChallengeDocument],
    destination: LoginCodeDestination,
    app_settings: AppSettings,
) -> None:
    same_budget: list[OtpChallengeDocument] = list_same_budget(recent, destination)
    budget_cap: LoginCodeCap = (
        LoginCodeCap.VERIFIED_USERS
        if destination.is_verified_destination
        else LoginCodeCap.NEW_DESTINATIONS
    )
    budget_limit: OtpSendLimit = find_budget_limit(destination, app_settings)
    if len(same_budget) >= int(budget_limit):
        raise LoginCodeCapReachedError(
            TOO_MANY_CODES_MESSAGE,
            alert=LoginCodeCapAlert(cap=budget_cap, limit=budget_limit),
        )

    if (
        destination.is_verified_destination
        or destination.login_method is not LoginMethod.PHONE
    ):
        return

    country_limit: OtpSendLimit = app_settings.otp_sends_per_country_per_hour
    if len(
        [
            challenge
            for challenge in same_budget
            if challenge.login_method is LoginMethod.PHONE
            and challenge.country_code == destination.country_code
        ]
    ) >= int(country_limit):
        raise LoginCodeCapReachedError(
            TOO_MANY_CODES_MESSAGE,
            alert=LoginCodeCapAlert(
                cap=LoginCodeCap.COUNTRY,
                limit=country_limit,
                country_code=destination.country_code,
            ),
        )


def list_same_budget(
    recent: list[OtpChallengeDocument],
    destination: LoginCodeDestination,
) -> list[OtpChallengeDocument]:
    """The recent challenges counted against the destination's platform cap."""

    return [
        challenge
        for challenge in recent
        if challenge.is_verified_destination == destination.is_verified_destination
    ]


def find_budget_limit(
    destination: LoginCodeDestination,
    app_settings: AppSettings,
) -> OtpSendLimit:
    if destination.is_verified_destination:
        return app_settings.otp_sends_to_verified_users_per_hour

    return app_settings.otp_sends_per_hour


def is_same_destination(
    challenge: OtpChallengeDocument,
    destination: LoginCodeDestination,
) -> bool:
    return (
        destination.phone_number is not None
        and challenge.phone_number == destination.phone_number
    ) or (destination.email is not None and challenge.email == destination.email)

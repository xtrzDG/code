"""How often login codes may be sent: per destination, address and in total."""

import logging

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.repositories.user_repositories import OtpChallengeRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress

logger: logging.Logger = logging.getLogger(__name__)
RESEND_INTERVAL_SECONDS: int = 30
LIMIT_WINDOW_SECONDS: int = 60 * 60
TOO_MANY_CODES_MESSAGE: str = "Too many login codes were requested. Try again later."


def refuse_over_login_code_limits(
    otp_challenge_repo: OtpChallengeRepoContract,
    wall_clock: WallClock[Microseconds],
    app_settings: AppSettings,
    phone_number: E164PhoneNumber | None,
    email: EmailAddress | None,
    requested_channel: OtpDeliveryChannel | None,
    client_ip_address: ClientIpAddress | None,
) -> None:
    """
    Refuse a send within 30 seconds of the last one to the same
    destination and channel (a phone may switch to another channel at
    once), or over the hourly caps per destination, per client address
    and in total.
    """

    settings: AppSettings = app_settings
    resend_start: int = int(
        wall_clock.now_unix_with_delta(Seconds(-RESEND_INTERVAL_SECONDS))
    )
    recent: list[OtpChallengeDocument] = otp_challenge_repo.list_created_since(
        wall_clock.now_unix_with_delta(Seconds(-LIMIT_WINDOW_SECONDS))
    )
    same_destination: list[OtpChallengeDocument] = [
        challenge
        for challenge in recent
        if (phone_number is not None and challenge.phone_number == phone_number)
        or (email is not None and challenge.email == email)
    ]
    if any(
        int(challenge.created_at) > resend_start
        and (
            phone_number is None
            or requested_channel is None
            or challenge.delivery_channel == requested_channel
        )
        for challenge in same_destination
    ):
        raise RateLimitedError(
            f"A code was just sent. Wait {RESEND_INTERVAL_SECONDS} seconds "
            "before asking for another one."
        )

    if len(same_destination) >= int(settings.otp_sends_per_destination_per_hour):
        raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

    if client_ip_address is not None and len(
        [
            challenge
            for challenge in recent
            if challenge.requested_from_ip == client_ip_address
        ]
    ) >= int(settings.otp_sends_per_ip_per_hour):
        raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

    if len(recent) >= int(settings.otp_sends_per_hour):
        logger.warning(
            "The hourly cap of %s login codes is reached; sends are refused.",
            int(settings.otp_sends_per_hour),
        )
        raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

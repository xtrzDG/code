"""How often login codes may be checked: per client network and per challenge."""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.utilities.channels.widget_rate_limits import describe_client_network

CHECK_WINDOW_SECONDS: int = 10 * 60
# Requests per challenge in the window. Only `otp_max_failed_attempts` of
# them are ever compared with the code; the rest are refused cheaply.
CHECKS_PER_CHALLENGE: int = 10
TOO_MANY_CHECKS_MESSAGE: str = "Too many code checks. Wait a few minutes and try again."


def refuse_too_frequent_code_checks(
    rate_limit_registry: RequestRateLimitRegistryContract,
    app_settings: AppSettings,
    challenge_id: OtpChallengeId,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Count one code check for its challenge and its client network (one IPv4
    address or the /64 of an IPv6 address), or for neither, in sliding
    windows of ten minutes. The attempt limit of a challenge stops guessing
    one code; this limit stops one network from guessing many codes at once
    (a fresh challenge for every 5 guesses).

    Raises:
        RateLimitedError: a limit is used up; it carries the seconds until
            the limit frees a place (Retry-After).
    """

    counters: list[tuple[str, int]] = [
        (f"otp-check:challenge:{challenge_id}", CHECKS_PER_CHALLENGE)
    ]
    if client_ip_address is not None:
        counters.append(
            (
                f"otp-check:address:{describe_client_network(client_ip_address)}",
                int(app_settings.otp_verifies_per_ip_per_10_minutes),
            )
        )

    refused_key: str | None = rate_limit_registry.try_acquire_all(
        counters, CHECK_WINDOW_SECONDS, now
    )
    if refused_key is None:
        return

    refused_limit: int = dict(counters)[refused_key]
    raise RateLimitedError(
        TOO_MANY_CHECKS_MESSAGE,
        retry_after_seconds=RetryAfterSeconds(
            rate_limit_registry.seconds_until_free(
                refused_key, refused_limit, CHECK_WINDOW_SECONDS, now
            )
        ),
    )

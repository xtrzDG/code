"""
How often codes may be checked, one policy for every kind of code: a login
code, an authenticator or recovery code at sign-in, a code confirming an
action. Each check counts once for its subject (a login challenge, a
sign-in step, a person confirming) and once for its client network (one
IPv4 address or the /64 of an IPv6 address), in sliding windows of ten
minutes. The network budget is shared by every kind of code, so one
network cannot guess codes of many accounts by switching between them.
"""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import describe_client_network

CHECK_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(10 * 60)
TOO_MANY_CHECKS_MESSAGE: str = "Too many code checks. Wait a few minutes and try again."


def refuse_too_frequent_checks(
    rate_limit_registry: RequestRateLimitRegistryContract,
    app_settings: AppSettings,
    subject: RateLimitCounter,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Count one check for `subject` and for the client network (when known),
    both or neither.

    Raises:
        RateLimitedError: a limit is used up; it carries the seconds until
            the limit frees a place (Retry-After).
    """

    counters: list[RateLimitCounter] = [subject]
    if client_ip_address is not None:
        counters.append(
            RateLimitCounter(
                key=RateLimitKey(
                    f"otp-check:address:{describe_client_network(client_ip_address)}"
                ),
                limit=RequestsPerWindow(
                    int(app_settings.otp_verifies_per_ip_per_10_minutes)
                ),
            )
        )

    refused_key: RateLimitKey | None = rate_limit_registry.try_acquire_all(
        counters, CHECK_WINDOW_SECONDS, now
    )
    if refused_key is None:
        return

    refused: RateLimitCounter = next(
        counter for counter in counters if counter.key == refused_key
    )
    raise RateLimitedError(
        TOO_MANY_CHECKS_MESSAGE,
        retry_after_seconds=rate_limit_registry.seconds_until_free(
            refused, CHECK_WINDOW_SECONDS, now
        ),
    )

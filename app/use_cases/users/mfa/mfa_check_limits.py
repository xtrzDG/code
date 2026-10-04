"""How often authenticator and recovery codes may be checked."""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RequestsPerWindow
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.users.otp_login.login_check_limits import (
    CHECK_WINDOW_SECONDS,
    TOO_MANY_CHECKS_MESSAGE,
)
from app.utilities.channels.widget_rate_limits import describe_client_network

# Checks of one sign-in step or of one person's confirmations in ten
# minutes; a sign-in step locks after five wrong codes anyway.
CHECKS_PER_SUBJECT: RequestsPerWindow = RequestsPerWindow(10)


def refuse_too_frequent_second_factor_checks(
    rate_limit_registry: RequestRateLimitRegistryContract,
    app_settings: AppSettings,
    subject: RateLimitKey,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Count one check for its subject (a sign-in step, or a person confirming
    an action) and for the client network, which shares its budget with
    the login code checks: one network cannot guess codes of many accounts.

    Raises:
        RateLimitedError: a limit is used up (with Retry-After).
    """

    counters: list[RateLimitCounter] = [
        RateLimitCounter(key=subject, limit=CHECKS_PER_SUBJECT)
    ]
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

"""How often authenticator and recovery codes may be checked."""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RequestsPerWindow
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.users.check_limit_policy import refuse_too_frequent_checks

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
    the login code checks (check_limit_policy): one network cannot guess
    codes of many accounts.

    Raises:
        RateLimitedError: a limit is used up (with Retry-After).
    """

    refuse_too_frequent_checks(
        rate_limit_registry,
        app_settings,
        RateLimitCounter(key=subject, limit=CHECKS_PER_SUBJECT),
        client_ip_address,
        now,
    )

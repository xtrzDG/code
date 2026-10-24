"""How often login codes may be checked: per client network and per challenge."""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RequestsPerWindow
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.use_cases.users.check_limit_policy import refuse_too_frequent_checks

# Requests per challenge in the window. Only `otp_max_failed_attempts` of
# them are ever compared with the code; the rest are refused cheaply.
CHECKS_PER_CHALLENGE: RequestsPerWindow = RequestsPerWindow(10)


def refuse_too_frequent_code_checks(
    rate_limit_registry: RequestRateLimitRegistryContract,
    app_settings: AppSettings,
    challenge_id: OtpChallengeId,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Count one code check for its challenge and its client network
    (check_limit_policy). The attempt limit of a challenge stops guessing
    one code; the network limit stops one network from guessing many codes
    at once (a fresh challenge for every 5 guesses).

    Raises:
        RateLimitedError: a limit is used up (with Retry-After).
    """

    refuse_too_frequent_checks(
        rate_limit_registry,
        app_settings,
        RateLimitCounter(
            key=RateLimitKey(f"otp-check:challenge:{challenge_id}"),
            limit=CHECKS_PER_CHALLENGE,
        ),
        client_ip_address,
        now,
    )

"""How often one sign-in step or one person may ask for passkey options."""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey

PASSKEY_REQUEST_WINDOW: RateWindowSeconds = RateWindowSeconds(10 * 60)
# Options asked for by one sign-in step, or by one person (adding a passkey,
# confirming an action), in ten minutes: each stores a challenge row. The
# answers count against the second-factor check limits.
PASSKEY_REQUESTS_PER_SUBJECT: RequestsPerWindow = RequestsPerWindow(10)
TOO_MANY_REQUESTS_MESSAGE: str = (
    "Too many passkey requests. Wait a few minutes and try again."
)


def refuse_too_many_passkey_requests(
    rate_limit_registry: RequestRateLimitRegistryContract,
    subject: RateLimitKey,
    now: Microseconds,
) -> None:
    """
    Raises:
        RateLimitedError: the subject's budget is used up (with Retry-After).
    """

    counter = RateLimitCounter(key=subject, limit=PASSKEY_REQUESTS_PER_SUBJECT)
    if (
        rate_limit_registry.try_acquire_all([counter], PASSKEY_REQUEST_WINDOW, now)
        is None
    ):
        return

    raise RateLimitedError(
        TOO_MANY_REQUESTS_MESSAGE,
        retry_after_seconds=rate_limit_registry.seconds_until_free(
            counter, PASSKEY_REQUEST_WINDOW, now
        ),
    )

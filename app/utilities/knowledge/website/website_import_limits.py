"""
How often a business may import its website: 10 imports in any hour
(each reads up to 15 pages with a model call per page), counted for every
API instance together.
"""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey

IMPORTS_PER_HOUR: RequestsPerWindow = RequestsPerWindow(10)
HOUR: RateWindowSeconds = RateWindowSeconds(60 * 60)
KEY_PREFIX: str = "website-import:business"


def refuse_too_many_imports(
    rate_limit_registry: RequestRateLimitRegistryContract,
    business_id: BusinessId,
    now: Microseconds,
) -> None:
    """
    Count one import of the business.

    Raises:
        RateLimitedError: the business started 10 imports in the last hour
            (HTTP 429 with Retry-After).
    """

    counter = RateLimitCounter(
        key=RateLimitKey(f"{KEY_PREFIX}:{business_id}"), limit=IMPORTS_PER_HOUR
    )
    if rate_limit_registry.try_acquire_all([counter], HOUR, now) is None:
        return

    raise RateLimitedError(
        "The website was imported 10 times in the last hour; try again later.",
        retry_after_seconds=rate_limit_registry.seconds_until_free(counter, HOUR, now),
    )

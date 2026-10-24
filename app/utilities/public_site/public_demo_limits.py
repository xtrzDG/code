"""
Limits of the landing page's sandbox demos. Anyone can write to a demo and
every message is a model call the platform pays for, so each message counts,
in one-hour windows of `RequestRateLimitRegistryContract`, against the
visitor's conversation, the visitor's network, the demo business and the
whole public site (PUBLIC_DEMO_MESSAGES_PER_HOUR). A message is counted for
all of them or, refused, for none, and answered with HTTP 429 and a
Retry-After.
"""

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.public_site.constrained_integers import (
    PublicDemoMessagesPerHour,
)
from app.schemas.typings.public_site.constrained_strings import PublicDemoSessionKey
from app.utilities.channels.widget_rate_limits import describe_client_network

PUBLIC_DEMO_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(60 * 60)
# A visitor trying the assistant asks a handful of questions; twenty in an
# hour is a long conversation.
PUBLIC_DEMO_MESSAGES_PER_CONVERSATION: int = 20
# An office or a mobile network shares one address: room for a few visitors.
PUBLIC_DEMO_MESSAGES_PER_NETWORK: int = 60
# One demo business among the visitors of a busy hour.
PUBLIC_DEMO_MESSAGES_PER_BUSINESS: int = 600
PUBLIC_DEMO_REFUSAL: str = (
    "You have sent the demo many messages; try again later or create your "
    "own assistant."
)


def refuse_too_many_demo_messages(
    rate_limit_registry: RequestRateLimitRegistryContract,
    business_id: BusinessId,
    session_key: PublicDemoSessionKey,
    client_ip_address: ClientIpAddress | None,
    site_messages_per_hour: PublicDemoMessagesPerHour,
    now: Microseconds,
) -> None:
    """
    Count the message for its conversation, network (when known), demo
    business and the public site, or for none of them.

    Raises:
        RateLimitedError: one of the limits is used up; it carries the
            seconds until that limit frees a place (Retry-After).
    """

    counters: list[RateLimitCounter] = [
        counter(
            f"public-demo:conversation:{business_id}:{session_key}",
            PUBLIC_DEMO_MESSAGES_PER_CONVERSATION,
        )
    ]
    if client_ip_address is not None:
        counters.append(
            counter(
                "public-demo:network:" + describe_client_network(client_ip_address),
                PUBLIC_DEMO_MESSAGES_PER_NETWORK,
            )
        )
    counters.extend(
        [
            counter(
                f"public-demo:business:{business_id}",
                PUBLIC_DEMO_MESSAGES_PER_BUSINESS,
            ),
            counter("public-demo:site", int(site_messages_per_hour)),
        ]
    )
    refused_key: RateLimitKey | None = rate_limit_registry.try_acquire_all(
        counters, PUBLIC_DEMO_WINDOW_SECONDS, now
    )
    if refused_key is None:
        return

    refused: RateLimitCounter = next(
        candidate for candidate in counters if candidate.key == refused_key
    )
    raise RateLimitedError(
        PUBLIC_DEMO_REFUSAL,
        retry_after_seconds=rate_limit_registry.seconds_until_free(
            refused, PUBLIC_DEMO_WINDOW_SECONDS, now
        ),
    )


def counter(key: str, limit: int) -> RateLimitCounter:
    return RateLimitCounter(key=RateLimitKey(key), limit=RequestsPerWindow(limit))

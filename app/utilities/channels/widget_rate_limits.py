"""
Rate limits of the public website-widget routes. Anyone can call them, so
each kind of request is limited per visitor (the widget's session key in
one business) and per client address (any business), in sliding windows of
a minute kept by `RequestRateLimitRegistryContract`. A refused request is
answered with HTTP 429 and a Retry-After.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds

RATE_WINDOW_SECONDS: int = 60


@dataclass(frozen=True)
class WidgetRateLimits:
    """Requests of one kind per minute, and the English text of a refusal."""

    key_prefix: str
    per_visitor_per_minute: int
    per_address_per_minute: int
    refusal: str


# The widget polls every 4 s at the fastest (15 a minute per tab): room for
# a few tabs of one visitor, and for many visitors behind one address.
WIDGET_POLL_LIMITS: WidgetRateLimits = WidgetRateLimits(
    key_prefix="widget-poll",
    per_visitor_per_minute=60,
    per_address_per_minute=300,
    refusal="Too many requests; ask less often.",
)
# Every message makes the assistant answer (a model call). A person waits
# for each answer, so a message every 5 s is generous; an address carries a
# few busy visitors (an office, a shared mobile network address).
WIDGET_MESSAGE_LIMITS: WidgetRateLimits = WidgetRateLimits(
    key_prefix="widget-message",
    per_visitor_per_minute=12,
    per_address_per_minute=60,
    refusal="Too many messages; wait a moment before sending another.",
)


def refuse_too_frequent_widget_requests(
    rate_limit_registry: RequestRateLimitRegistryContract,
    limits: WidgetRateLimits,
    business_id: BusinessId,
    session_key: WidgetSessionKey,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """
    Count the request for its visitor and its address (when known).

    Raises:
        RateLimitedError: one of the limits is used up; it carries the
            seconds until that limit frees a place (Retry-After).
    """

    counters: list[tuple[str, int]] = [
        (
            f"{limits.key_prefix}:visitor:{business_id}:{session_key}",
            limits.per_visitor_per_minute,
        )
    ]
    if client_ip_address is not None:
        counters.append(
            (
                f"{limits.key_prefix}:address:{client_ip_address}",
                limits.per_address_per_minute,
            )
        )

    for key, limit in counters:
        if rate_limit_registry.try_acquire(key, limit, RATE_WINDOW_SECONDS, now):
            continue

        wait_seconds: int = rate_limit_registry.seconds_until_free(
            key, limit, RATE_WINDOW_SECONDS, now
        )
        raise RateLimitedError(
            limits.refusal,
            retry_after_seconds=RetryAfterSeconds(max(1, wait_seconds)),
        )

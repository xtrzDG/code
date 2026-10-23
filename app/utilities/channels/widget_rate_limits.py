"""
Rate limits of the public website-widget routes. Anyone can call them, and
every message makes the assistant answer (a model call), so each kind of
request is limited per visitor (the widget's session key in one business),
per client network (one IPv4 address, or the /64 of an IPv6 address: one
host or home gets a whole /64), per business and for the whole platform, in
sliding windows of a minute kept by `RequestRateLimitRegistryContract`. The
session key is chosen by the caller, so only the other limits bound a
script; the business and platform limits bound the model spend even across
many networks. A request is counted for all of them or, refused, for none
(it leaves no state behind), and answered with HTTP 429 and a Retry-After.

Polls are the one kind every open chat sends all the time (each tab every
4 s): their business and platform counters are leased (each process
takes 1% of the limit at a time and admits from it, `RateLimitLeases`),
so polls do not queue on those two shared rows; the visitor and network
counters stay one count per poll in the shared counters, so one visitor or
one network is held to its limit across every API process exactly.
"""

import ipaddress
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseSize,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey

RATE_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(60)
IPV6_NETWORK_PREFIX_LENGTH: int = 64


@dataclass(frozen=True)
class WidgetRateLimits:
    """
    Requests of one kind per minute, and the English text of a refusal.
    A lease size makes each process take that many requests of the
    business (or platform) counter at a time (None: one count per request).
    """

    key_prefix: str
    per_visitor_per_minute: int
    per_address_per_minute: int
    per_business_per_minute: int
    per_platform_per_minute: int
    refusal: str
    business_lease_size: RateLimitLeaseSize | None = None
    platform_lease_size: RateLimitLeaseSize | None = None


# The widget polls every 4 s at the fastest (15 a minute per tab): room for
# a few tabs of one visitor, for many visitors behind one address and for
# hundreds of open chats of one business. The business and platform
# counters are leased 1% at a time (topped up when a fifth is left): with N
# API processes the limit may bind up to 1.2 x N % early, never late.
WIDGET_POLL_LIMITS: WidgetRateLimits = WidgetRateLimits(
    key_prefix="widget-poll",
    per_visitor_per_minute=60,
    per_address_per_minute=300,
    per_business_per_minute=6_000,
    per_platform_per_minute=60_000,
    refusal="Too many requests; ask less often.",
    business_lease_size=RateLimitLeaseSize(60),
    platform_lease_size=RateLimitLeaseSize(600),
)
# Every message makes the assistant answer (a model call). A person waits
# for each answer, so a message every 5 s is generous; an address carries a
# few busy visitors (an office, a shared mobile network address); a business
# gets dozens of chatting visitors at once.
WIDGET_MESSAGE_LIMITS: WidgetRateLimits = WidgetRateLimits(
    key_prefix="widget-message",
    per_visitor_per_minute=12,
    per_address_per_minute=60,
    per_business_per_minute=120,
    per_platform_per_minute=1_200,
    refusal="Too many messages; wait a moment before sending another.",
)

# "Talk to a person" notifies staff: a visitor asks once or twice, and a
# script must not page the team every second.
WIDGET_HANDOFF_LIMITS: WidgetRateLimits = WidgetRateLimits(
    key_prefix="widget-handoff",
    per_visitor_per_minute=3,
    per_address_per_minute=10,
    per_business_per_minute=30,
    per_platform_per_minute=600,
    refusal="Too many requests for a person; wait a moment and try again.",
)

# A photo or a voice note: a person sends a few in a conversation, each
# stored (and read by the model) once its message is sent.
WIDGET_UPLOAD_LIMITS: WidgetRateLimits = WidgetRateLimits(
    key_prefix="widget-upload",
    per_visitor_per_minute=6,
    per_address_per_minute=30,
    per_business_per_minute=120,
    per_platform_per_minute=1_200,
    refusal="Too many files; wait a moment before sending another.",
)
# Thumbs up or down on an answer: a visitor changes their mind once or
# twice; nothing above that is a person.
WIDGET_RATING_LIMITS: WidgetRateLimits = WidgetRateLimits(
    key_prefix="widget-rating",
    per_visitor_per_minute=6,
    per_address_per_minute=60,
    per_business_per_minute=600,
    per_platform_per_minute=6_000,
    refusal="Too many ratings; wait a moment and try again.",
)


def describe_client_network(client_ip_address: ClientIpAddress) -> str:
    """
    The client network a rate-limit key counts (a technical key part): an
    IPv4 address as is, the /64 of an IPv6 address (rotating addresses of
    one network share it) and the IPv4 address inside an IPv4-mapped IPv6
    address. Anything else (a test client's host name) stays as it is.
    """

    try:
        address = ipaddress.ip_address(str(client_ip_address))
    except ValueError:
        return str(client_ip_address)

    if isinstance(address, ipaddress.IPv4Address):
        return str(address)

    if address.ipv4_mapped is not None:
        return str(address.ipv4_mapped)

    return str(
        ipaddress.IPv6Network(
            (address, IPV6_NETWORK_PREFIX_LENGTH),
            strict=False,
        )
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
    Count the request for its visitor, its network (when known), its
    business and the platform, or for none of them.

    Raises:
        RateLimitedError: one of the limits is used up; it carries the
            seconds until that limit frees a place (Retry-After).
    """

    counters: list[RateLimitCounter] = [
        RateLimitCounter(
            key=RateLimitKey(
                f"{limits.key_prefix}:visitor:{business_id}:{session_key}"
            ),
            limit=RequestsPerWindow(limits.per_visitor_per_minute),
        )
    ]
    if client_ip_address is not None:
        counters.append(
            RateLimitCounter(
                key=RateLimitKey(
                    f"{limits.key_prefix}:address:"
                    f"{describe_client_network(client_ip_address)}"
                ),
                limit=RequestsPerWindow(limits.per_address_per_minute),
            )
        )
    counters.extend(
        [
            RateLimitCounter(
                key=RateLimitKey(f"{limits.key_prefix}:business:{business_id}"),
                limit=RequestsPerWindow(limits.per_business_per_minute),
                lease_size=limits.business_lease_size,
            ),
            RateLimitCounter(
                key=RateLimitKey(f"{limits.key_prefix}:platform"),
                limit=RequestsPerWindow(limits.per_platform_per_minute),
                lease_size=limits.platform_lease_size,
            ),
        ]
    )
    refuse_over_limits(rate_limit_registry, counters, limits.refusal, now)


def refuse_over_limits(
    rate_limit_registry: RequestRateLimitRegistryContract,
    counters: list[RateLimitCounter],
    refusal: str,
    now: Microseconds,
) -> None:
    """
    Count one request against every counter in a one-minute window, or
    against none of them.

    Raises:
        RateLimitedError: one of the limits is used up; it carries the
            seconds until that limit frees a place (Retry-After).
    """

    refused_key: RateLimitKey | None = rate_limit_registry.try_acquire_all(
        counters,
        RATE_WINDOW_SECONDS,
        now,
    )
    if refused_key is None:
        return

    refused: RateLimitCounter = next(
        counter for counter in counters if counter.key == refused_key
    )
    raise RateLimitedError(
        refusal,
        retry_after_seconds=rate_limit_registry.seconds_until_free(
            refused, RATE_WINDOW_SECONDS, now
        ),
    )

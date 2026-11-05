"""
How many new website conversations one client network may start in an
hour (ABUSE-03). The widget and the hosted chat take a session key the
caller chooses, so a script can start a fresh conversation with every
message; per-minute message limits do not bound that, and every first
message costs a model call. A new conversation from a network (an IPv4
address, or the /64 of an IPv6 address) past `PER_BUSINESS_PER_HOUR` for
one business, or past `PER_PLATFORM_PER_HOUR` across every business, gets
the polite limit notice instead of the model (its message still reaches
the team's inbox); the next message of that conversation is answered as
usual, so a real person behind a busy network loses one answer at most.
Only public addresses count: a loopback or private address is a local
test, the preview stand or a proxy that hides its clients, never one
network to hold back.
"""

import ipaddress

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import describe_client_network

HOUR: RateWindowSeconds = RateWindowSeconds(60 * 60)
PER_BUSINESS_PER_HOUR: RequestsPerWindow = RequestsPerWindow(20)
PER_PLATFORM_PER_HOUR: RequestsPerWindow = RequestsPerWindow(120)
KEY_PREFIX: str = "new-conversation:network"


def is_past_network_conversation_cap(
    rate_limits: RequestRateLimitRegistryContract,
    message: InboundMessage,
    is_new_conversation: bool,
    is_sandbox: bool,
    now: Microseconds,
) -> bool:
    """
    Count a new conversation of a known network; True when it is past a
    cap (and is then not counted). Other messages are not counted.
    """

    if not is_new_conversation or is_sandbox or message.client_ip_address is None:
        return False

    if not is_public_address(str(message.client_ip_address)):
        return False

    network: str = describe_client_network(message.client_ip_address)
    counters: list[RateLimitCounter] = [
        RateLimitCounter(
            key=RateLimitKey(f"{KEY_PREFIX}:{message.business_id}:{network}"),
            limit=PER_BUSINESS_PER_HOUR,
        ),
        RateLimitCounter(
            key=RateLimitKey(f"{KEY_PREFIX}:{network}"),
            limit=PER_PLATFORM_PER_HOUR,
        ),
    ]
    return rate_limits.try_acquire_all(counters, HOUR, now) is not None


def is_public_address(address: str) -> bool:
    """An address of the public internet (not loopback, private or reserved)."""

    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False

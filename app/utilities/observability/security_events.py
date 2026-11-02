"""
Security events as structured log lines: one logger (`app.security`), one
helper and a few stable event names, so a log search or an alert finds
every refusal of one kind by its `security_event` field.

A line names what happened and where, never who: the route template, the
provider of a webhook, the reason (a short code) and the client network
(an IPv4 /24 or an IPv6 /48, never the address itself). No tokens, bodies,
names, phone numbers or e-mail addresses.
"""

import ipaddress
import logging

from app.utilities.observability.log_formatting import log_fields

SECURITY_LOGGER: logging.Logger = logging.getLogger("app.security")

# A webhook delivery refused (unsigned, badly signed, stale, a flood).
WEBHOOK_DELIVERY_REFUSED: str = "webhook_delivery_refused"
# A request without valid credentials (401) or without the right (403).
AUTHORIZATION_DENIED: str = "authorization_denied"
# A request refused by a rate limit or a flood budget (429).
RATE_LIMIT_TRIGGERED: str = "rate_limit_triggered"
# A request body refused before it was parsed (too large, nested too deep).
REQUEST_BODY_REFUSED: str = "request_body_refused"
# An API request that did not answer within its deadline (504).
REQUEST_DEADLINE_EXCEEDED: str = "request_deadline_exceeded"

IPV4_LOGGED_PREFIX_LENGTH: int = 24
IPV6_LOGGED_PREFIX_LENGTH: int = 48
UNKNOWN_NETWORK: str = "unknown"


def describe_logged_network(client_address: str | None) -> str:
    """
    The client network a security line names: the /24 of an IPv4 address
    (also inside an IPv4-mapped IPv6 one), the /48 of an IPv6 address,
    "unknown" for anything else (no address, a test client's host name).
    """

    if client_address is None:
        return UNKNOWN_NETWORK

    try:
        address = ipaddress.ip_address(client_address.strip())
    except ValueError:
        return UNKNOWN_NETWORK

    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped

    prefix_length: int = (
        IPV4_LOGGED_PREFIX_LENGTH
        if isinstance(address, ipaddress.IPv4Address)
        else IPV6_LOGGED_PREFIX_LENGTH
    )
    network = ipaddress.ip_network(f"{address}/{prefix_length}", strict=False)
    return str(network)


def log_security_event(
    event: str,
    *,
    path: str,
    reason: str,
    client_address: str | None,
    **fields: int | str,
) -> None:
    """
    One warning line of `event` with its fields: `path` (a route template
    or a fixed path, never one with ids or a query), `reason` (a short
    code), the client network of `client_address` and the event's own
    fields (`provider`, `method`, `status`).
    """

    SECURITY_LOGGER.warning(
        "Security event %s: %s %s",
        event,
        reason,
        path,
        extra=log_fields(
            security_event=event,
            path=path,
            reason=reason,
            client_network=describe_logged_network(client_address),
            **fields,
        ),
    )

"""
A route's own flood budget per client network (`flood_budgets`), as a
dependency: past it the route answers 429 with Retry-After before it does
any work. For public routes every page load calls (the widget's config)
and probes anyone can reach (/readyz).
"""

import ipaddress
import time
from collections.abc import Callable

from fastapi import Request

from app.gateways.http.middleware.flood_budgets import (
    BudgetDecision,
    FloodBudget,
    MonotonicClock,
    network_key,
)
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds

type NetworkBudgetDependency = Callable[[Request], None]


def build_network_budget(
    label: str,
    per_minute: int,
    message: str,
    *,
    spare_private_networks: bool = False,
    clock: MonotonicClock = time.monotonic,
) -> NetworkBudgetDependency:
    """
    The dependency spending one request of the caller's network. With
    `spare_private_networks`, callers from a private or loopback address
    (the platform's own health checks, inside its network) are not counted.
    """

    budget = FloodBudget(per_minute, clock=clock)

    def spend_network_budget(request: Request) -> None:
        address: str | None = None if request.client is None else request.client.host
        if spare_private_networks and is_private_address(address):
            return

        decision: BudgetDecision = budget.spend(network_key(label, address))
        if not decision.is_admitted:
            raise RateLimitedError(
                message,
                retry_after_seconds=RetryAfterSeconds(decision.retry_after_seconds),
            )

    return spend_network_budget


def is_private_address(address: str | None) -> bool:
    """A loopback, private or link-local address (not one of the internet)."""

    if address is None:
        return False

    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False

    return parsed.is_private or parsed.is_loopback or parsed.is_link_local

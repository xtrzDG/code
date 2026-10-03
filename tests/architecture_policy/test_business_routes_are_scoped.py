"""
Storage scope policy (fail-closed, docs/architecture.md "Данные"):

- every route under /v1/businesses/{business_id} reaches its pipelines only
  through `BusinessScopedPipelineOperator`, so it runs in the storage scope
  of its business and row-level security hides every other business;
- platform-wide operators, the explicit escalation, are exactly the
  reviewed list below: adding one means adding it here with its reason.
"""

import typing
from collections.abc import Iterator, Sequence

from fastapi import APIRouter
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from app.operators.business_scoped_pipeline_operator import (
    BusinessScopedPipelineOperator,
)
from app.operators.platform_wide_pipeline_operator import (
    PlatformWidePipelineOperator,
)
from tests.e2e.harness import start_workshop

BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"
# Operators that run platform-wide, by container context, and why.
PLATFORM_WIDE_OPERATORS: dict[str, str] = {
    "billing.process_payment_webhook_operator": "payment webhook: order first",
    "billing.end_trials_operator": "periodic job over every business",
    "billing.enforce_grace_periods_operator": "periodic job over every business",
    "billing.check_package_usage_operator": "periodic job over every business",
    "billing.invoice_usage_overage_operator": "periodic job over every business",
    "calls.pbx_call_webhook_operator": "telephony webhook: business from the line",
    "channels.telegram_webhook_operator": "webhook: business from the channel",
    "channels.meta_webhook_operator": "webhook: business from the channel",
    "channels.handle_platform_bot_update_operator": "staff bot: link codes",
    "channels.process_platform_bot_update_operator": "staff bot job",
    "compliance.purge_expired_recordings_operator": "retention over every business",
    "conversations.voice_tool_webhook_operator": "voice webhook, then scoped",
    "conversations.post_call_webhook_operator": "voice webhook: agent first",
    "conversations.process_post_call_operator": "after-call job: agent first",
    "conversations.start_voice_call_operator": "voice webhook: agent first",
    "demo.seed_demo_data_operator": "development demo data",
    "demo.seed_load_operator": "load-test dataset across businesses (CLI)",
    "operations.complete_google_calendar_connection_operator": "consent state",
    "operations.send_booking_reminders_operator": "periodic job over every business",
    "platform.list_clients_operator": "platform admin's client list",
    "platform.purge_stale_rows_operator": "periodic purge over every business",
    "security.rotate_encrypted_secrets_operator": "re-encryption over every business",
}


def reachable_operators(function: object, seen: set[int]) -> Iterator[object]:
    """Operators a route endpoint calls, through the closures it captured."""

    if id(function) in seen:
        return

    seen.add(id(function))
    for cell in getattr(function, "__closure__", None) or ():
        value: object = cell.cell_contents
        if hasattr(value, "operate"):
            yield value
        elif callable(value):
            yield from reachable_operators(value, seen)


def api_routes(routes: Sequence[BaseRoute]) -> Iterator[APIRoute]:
    """The API routes of an app, also those of included routers."""

    for route in routes:
        if isinstance(route, APIRoute):
            yield route

        included: object = getattr(route, "original_router", None)
        if isinstance(included, APIRouter):
            yield from api_routes(included.routes)


def test_business_routes_run_in_the_scope_of_their_business() -> None:
    application = start_workshop().application
    business_routes = [
        route
        for route in api_routes(application.routes)
        if route.path.startswith(BUSINESS_PREFIX)
    ]
    unscoped: list[str] = []
    for route in business_routes:
        operators = list(reachable_operators(route.endpoint, set()))
        if not operators or not all(
            type(operator) is BusinessScopedPipelineOperator for operator in operators
        ):
            unscoped.append(
                f"{sorted(route.methods or ())} {route.path}: "
                f"{[type(operator).__name__ for operator in operators]}"
            )

    assert len(business_routes) >= 70
    assert unscoped == []


def test_platform_wide_operators_are_the_reviewed_ones() -> None:
    operators = start_workshop().container.operators
    platform_wide: set[str] = set()
    for context, child in operators.providers.items():
        for name, provider in getattr(child, "providers", {}).items():
            provided: object = getattr(provider, "cls", None)
            if (
                typing.get_origin(provided) or provided
            ) is PlatformWidePipelineOperator:
                platform_wide.add(f"{context}.{name}")

    assert platform_wide == set(PLATFORM_WIDE_OPERATORS)

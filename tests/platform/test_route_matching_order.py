"""
The public channel routes (webhooks and the website widget) are matched
first, and that changes no answer.

A request is matched against the routes one by one, so a widget poll used
to be compared with every cabinet route before its own. The channel router
now comes first; that is safe because no other route can match a channel
path and no channel route can match another route's path, so the first
match of every request is the same in any order.
"""

import re
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from starlette.routing import BaseRoute, Match, Route

from tests.e2e.harness import start_workshop

CHANNEL_ROUTES_MODULE: str = "app.gateways.http.channel_routes"
PATH_PARAMETER: re.Pattern[str] = re.compile(r"\{[^}]+\}")
WIDGET_POLL_PATH: str = (
    "/v1/widget/business_0b3c6e0e-8a3e-4d7e-9f0e-1d2c3b4a5f6e/messages"
)


@pytest.fixture(scope="module")
def application() -> FastAPI:
    return start_workshop().application


def flattened(routes: list[BaseRoute]) -> Iterator[BaseRoute]:
    """Every route in matching order, those of included routers in place."""

    for route in routes:
        included: object = getattr(route, "original_router", None)
        if included is not None:
            yield from flattened(list(getattr(included, "routes", [])))
        else:
            yield route


def path_routes(application: FastAPI) -> list[Route]:
    return [
        route
        for route in flattened(application.router.routes)
        if isinstance(route, Route)
    ]


def is_channel_route(route: Route) -> bool:
    return getattr(route.endpoint, "__module__", "") == CHANNEL_ROUTES_MODULE


def sample_path(route: Route) -> str:
    """The route's path with every parameter filled in."""

    return PATH_PARAMETER.sub("sample-1", route.path)


def http_scope(method: str, path: str) -> dict[str, object]:
    return {"type": "http", "method": method, "path": path, "root_path": ""}


class TestRouteMatchingOrder:
    def test_the_channel_routes_are_matched_before_every_other_route(
        self, application: FastAPI
    ) -> None:
        routes = path_routes(application)
        first_other = next(
            index
            for index, route in enumerate(routes)
            if not is_channel_route(route) and route.include_in_schema
        )

        channel_positions = [
            index for index, route in enumerate(routes) if is_channel_route(route)
        ]

        assert channel_positions
        assert max(channel_positions) < first_other

    def test_no_other_route_shares_a_path_with_a_channel_route(
        self, application: FastAPI
    ) -> None:
        routes = path_routes(application)
        channel = [route for route in routes if is_channel_route(route)]
        others = [route for route in routes if not is_channel_route(route)]

        overlaps = [
            f"{first.path} ~ {second.path}"
            for first in channel
            for second in others
            if first.path_regex.match(sample_path(second))
            or second.path_regex.match(sample_path(first))
        ]

        assert overlaps == []

    def test_a_widget_poll_is_answered_by_the_widget_messages_route(
        self, application: FastAPI
    ) -> None:
        matches = [
            route
            for route in path_routes(application)
            if route.matches(http_scope("GET", WIDGET_POLL_PATH))[0] is Match.FULL
        ]

        assert [route.name for route in matches] == ["list_widget_messages"]

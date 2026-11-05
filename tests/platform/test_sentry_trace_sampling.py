"""Sentry traces widget polls at a hundredth of SENTRY_TRACES_SAMPLE_RATE."""

import pytest

from app.facilitators.observability.sentry_trace_sampling import (
    WIDGET_POLL_TRACE_SHARE,
    build_trace_sampler,
    is_widget_poll,
)
from app.gateways.http.channel_routes import WIDGET_CONFIG_PATH, WIDGET_MESSAGES_PATH
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from tests.platform.test_sentry_reporting import enabled_reporter

RATE: TraceSampleRate = TraceSampleRate(0.05)
BUSINESS_ID: BusinessId = BusinessId()
POLL_PATH: str = WIDGET_MESSAGES_PATH.format(business_id=BUSINESS_ID)


def http(method: str, path: str) -> dict[str, object]:
    return {"type": "http", "method": method, "path": path}


@pytest.mark.parametrize(
    ("asgi_scope", "expected"),
    [
        (http("GET", POLL_PATH), float(RATE) * WIDGET_POLL_TRACE_SHARE),
        (http("POST", POLL_PATH), float(RATE)),
        (http("GET", WIDGET_CONFIG_PATH.format(business_id=BUSINESS_ID)), float(RATE)),
        (http("GET", f"/v1/businesses/{BUSINESS_ID}/conversations"), float(RATE)),
        (http("GET", f"{POLL_PATH}/more"), float(RATE)),
        ({"type": "websocket", "path": POLL_PATH}, float(RATE)),
        (None, float(RATE)),
    ],
)
def test_polls_are_traced_at_a_hundredth_of_the_rate(
    asgi_scope: object, expected: float
) -> None:
    sample = build_trace_sampler(RATE)

    assert sample({"asgi_scope": asgi_scope, "parent_sampled": None}) == (
        pytest.approx(expected)
    )


def test_a_parents_decision_is_kept() -> None:
    sample = build_trace_sampler(RATE)

    assert sample({"asgi_scope": http("GET", POLL_PATH), "parent_sampled": True}) == 1.0
    assert sample({"asgi_scope": http("GET", "/v1/me"), "parent_sampled": False}) == 0.0


def test_the_widget_poll_route_is_recognized() -> None:
    assert is_widget_poll(http("GET", POLL_PATH))
    assert not is_widget_poll(http("OPTIONS", POLL_PATH))
    assert not is_widget_poll("not a scope")


def test_sentry_gets_the_sampler() -> None:
    _, init = enabled_reporter()
    sample = init.options["traces_sampler"]

    assert init.options["traces_sample_rate"] == float(RATE)
    assert sample({"asgi_scope": http("GET", "/v1/me")}) == float(RATE)
    assert sample({"asgi_scope": http("GET", POLL_PATH)}) == pytest.approx(
        float(RATE) * WIDGET_POLL_TRACE_SHARE
    )

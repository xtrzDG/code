"""
Which API requests Sentry traces: SENTRY_TRACES_SAMPLE_RATE of them, but
widget polls at a hundredth of it.

Every open chat polls every 4 seconds, so polls are most of the API's
requests, and a traced request costs milliseconds of CPU in the process
(spans, the transaction, its sending): at 5 % the traced polls cost a poll
about a tenth more CPU on average (docs/operations/capacity.md, "Widget
polls: less Python per poll"). A poll is the same short read every time, so
a hundredth of the rate still shows its latency; every other request keeps
the configured rate, a request that carries a sampled trace (a parent's
decision) keeps that decision, and errors are reported as before.
"""

import re
from collections.abc import Callable, Mapping

from app.schemas.typings.platform.constrained_floats import TraceSampleRate

# GET /v1/widget/{business_id}/messages (the route is in channel_routes).
WIDGET_POLL_PATH: re.Pattern[str] = re.compile(r"^/v1/widget/[^/]+/messages$")
WIDGET_POLL_TRACE_SHARE: float = 0.01

type TraceSampler = Callable[[Mapping[str, object]], float]


def is_widget_poll(asgi_scope: object) -> bool:
    """Whether the ASGI scope of a request is a widget's poll."""

    if not isinstance(asgi_scope, Mapping):
        return False

    scope: Mapping[object, object] = asgi_scope
    path: object = scope.get("path")
    return (
        scope.get("type") == "http"
        and scope.get("method") == "GET"
        and isinstance(path, str)
        and WIDGET_POLL_PATH.match(path) is not None
    )


def build_trace_sampler(traces_sample_rate: TraceSampleRate) -> TraceSampler:
    """Sentry's `traces_sampler` for the configured rate (see the module)."""

    rate: float = float(traces_sample_rate)

    def sample(sampling_context: Mapping[str, object]) -> float:
        parent_sampled: object = sampling_context.get("parent_sampled")
        if isinstance(parent_sampled, bool):
            return 1.0 if parent_sampled else 0.0

        if is_widget_poll(sampling_context.get("asgi_scope")):
            return rate * WIDGET_POLL_TRACE_SHARE

        return rate

    return sample

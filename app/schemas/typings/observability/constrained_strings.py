"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class MetricsLabel(BaseConstrainedTypedString):
    """
    One label value of a Prometheus series: a route template, a provider, a
    model or a job name. Never an id, a text or an address, so the number
    of series stays bounded.

    Example:
        label = MetricsLabel("/v1/businesses/{business_id}/bookings")
    """

    min_length = 1
    max_length = 200
    pattern = r"^[\x21-\x7e]+$"


class OtelServiceName(BaseConstrainedTypedString):
    """
    The `service.name` of this process's OpenTelemetry spans
    (OTEL_SERVICE_NAME; `workshop-api` or `workshop-worker` by default).

    Example:
        name = OtelServiceName("workshop-api")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[a-z0-9][a-z0-9._-]*$"


class TraceId(BaseConstrainedTypedString):
    """
    The W3C trace id of a distributed trace (32 lowercase hex digits, not
    all zero): every span of one webhook, its jobs, model calls and sends.

    Example:
        trace_id = TraceId("4bf92f3577b34da6a3ce929d0e0e4736")
    """

    min_length = 32
    max_length = 32
    pattern = r"^(?!0{32})[0-9a-f]{32}$"


class TraceParent(BaseConstrainedTypedString):
    """
    A W3C `traceparent` value (version, trace id, parent span id, flags): a
    queued job keeps the one of the request or job that queued it, so its
    spans continue the same trace.

    Example:
        parent = TraceParent("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
    """

    min_length = 55
    max_length = 55
    pattern = r"^00-(?!0{32})[0-9a-f]{32}-(?!0{16})[0-9a-f]{16}-[0-9a-f]{2}$"


# Keep abc order for all non example types, if possible.

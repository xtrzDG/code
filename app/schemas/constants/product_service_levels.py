# Keep abc order for all non example types, if possible.
from enum import StrEnum


class ProductServiceLevel(StrEnum):
    """
    The product objectives past the first answer (docs/operations/slo.md,
    "Product objectives"); a name in reports and on the dashboard, never
    stored:

    - BOOKING_SUCCESS: booking tool calls that ended with a booking or a
      business answer, not an error (99.5%).
    - CALLS_ANSWERED: calls the voice platform took, over those plus the
      calls it could not take (99%).
    - NOTIFICATION_DELIVERY: outbox messages delivered, over all that
      settled (99%).
    - VOICE_LATENCY: days whose voice tool p95 stayed under 2 s (95%).
    - WEBHOOK_LAG: hours whose inbound pickup p99 stayed under 10 s (99%).
    """

    BOOKING_SUCCESS = "booking_success"
    CALLS_ANSWERED = "calls_answered"
    NOTIFICATION_DELIVERY = "notification_delivery"
    VOICE_LATENCY = "voice_latency"
    WEBHOOK_LAG = "webhook_lag"

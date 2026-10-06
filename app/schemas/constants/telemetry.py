"""Label values of the service metrics (docs/operations/observability.md)."""

from enum import StrEnum


class WebhookMessageOutcome(StrEnum):
    """What happened to one customer message a webhook brought."""

    RECEIVED = "received"
    # New: stored in the inbox and queued for the worker.
    QUEUED = "queued"
    # Delivered before (a platform's retry): neither stored nor answered again.
    DUPLICATE = "duplicate"


class OutboundAttemptOutcome(StrEnum):
    """How one send attempt of an outbox message ended."""

    DELIVERED = "delivered"
    # Failed for now; another attempt is queued.
    RETRY = "retry"
    # Failed for good: a refusal, no provider, or the last attempt.
    DEAD = "dead"


class LlmCallOutcome(StrEnum):
    """How one language-model call ended."""

    OK = "ok"
    # The provider failed (an outage, a timeout, a rate limit).
    ERROR = "error"
    # The model declined to answer (an answer, not a failure).
    REFUSED = "refused"


class ServiceLevelSeries(StrEnum):
    """
    The service level indicators counted in shared five-minute slots
    (docs/operations/slo.md): customer messages answered or handed off
    within 60 s of arriving, and API requests answered without a server
    error.
    """

    INBOUND_ANSWERED = "inbound_answered"
    API_AVAILABILITY = "api_availability"

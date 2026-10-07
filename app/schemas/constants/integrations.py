"""The public API and outbound webhooks (Settings → Integrations)."""

from enum import StrEnum


class BusinessEventType(StrEnum):
    """
    What a webhook endpoint can subscribe to: a change in the business, as
    the public API names it. A frozen list (docs/api-versioning.md): a new
    type is added only for endpoints that ask for it by name.

    `booking.cancelled` is sent instead of `booking.updated` when a change
    leaves the booking cancelled. `webhook.test` is the owner's "Send test
    event"; nobody subscribes to it.
    """

    BOOKING_CREATED = "booking.created"
    BOOKING_UPDATED = "booking.updated"
    BOOKING_CANCELLED = "booking.cancelled"
    LEAD_CREATED = "lead.created"
    LEAD_UPDATED = "lead.updated"
    HANDOFF_CREATED = "handoff.created"
    HANDOFF_RESOLVED = "handoff.resolved"
    CONVERSATION_STARTED = "conversation.started"
    CALL_FINISHED = "call.finished"
    WEBHOOK_TEST = "webhook.test"


# The types an endpoint may subscribe to (all but the test event).
SUBSCRIBABLE_EVENT_TYPES: tuple[BusinessEventType, ...] = tuple(
    event_type
    for event_type in BusinessEventType
    if event_type is not BusinessEventType.WEBHOOK_TEST
)


class WebhookEndpointStatus(StrEnum):
    """
    ACTIVE: events are sent. PAUSED: the owner paused it (nothing is
    queued). DISABLED: switched off after too many failed attempts in a
    row, or because the receiver answered 410 Gone; the owner turns it on
    again.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class WebhookEndpointOrigin(StrEnum):
    """
    CABINET: the owner added it in Settings → Integrations. API: a client
    of the public API subscribed it with an API key (a Zapier REST hook);
    it is removed when that client unsubscribes or the receiver answers
    410 Gone.
    """

    CABINET = "cabinet"
    API = "api"


class WebhookDeliveryStatus(StrEnum):
    """
    PENDING: waiting for its first or next attempt. DELIVERED: the receiver
    answered 2xx. FAILED: given up (24 hours of attempts, a refusal that a
    retry cannot fix, or the endpoint was switched off or removed).
    """

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class WebhookDeliveryProblem(StrEnum):
    """
    Why an attempt failed, in the terms the delivery log explains:

    - NOT_PUBLIC: the address is not a public https address (SSRF guard);
    - UNKNOWN_HOST, CONNECTION_FAILED, TIMEOUT, REQUEST_FAILED: the network;
    - HTTP_STATUS: the receiver answered 3xx (redirects are not followed),
      4xx or 5xx;
    - GONE: the receiver answered 410, so the endpoint is switched off;
    - ENDPOINT_OFF: the endpoint was paused, switched off or removed
      before the attempt.
    """

    NOT_PUBLIC = "not_public"
    UNKNOWN_HOST = "unknown_host"
    CONNECTION_FAILED = "connection_failed"
    TIMEOUT = "timeout"
    REQUEST_FAILED = "request_failed"
    HTTP_STATUS = "http_status"
    GONE = "gone"
    ENDPOINT_OFF = "endpoint_off"


class ApiKeyScope(StrEnum):
    """What an API key may do: read or create one kind of record."""

    BOOKINGS_READ = "bookings:read"
    BOOKINGS_WRITE = "bookings:write"
    LEADS_READ = "leads:read"
    LEADS_WRITE = "leads:write"
    CONTACTS_READ = "contacts:read"
    CONVERSATIONS_READ = "conversations:read"
    WEBHOOKS_MANAGE = "webhooks:manage"


class ApiKeyStatus(StrEnum):
    """ACTIVE keys are accepted; a REVOKED key is refused from then on."""

    ACTIVE = "active"
    REVOKED = "revoked"

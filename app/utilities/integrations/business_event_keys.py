"""
Which business events an announced change can become, and the ids of the
events and their deliveries (derived, so announcing a change twice never
queues it twice).
"""

from collections.abc import Mapping
from uuid import UUID, uuid5

from app.schemas.constants.integrations import BusinessEventType
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.prefixed_id import (
    BusinessEventId,
    WebhookDeliveryId,
    WebhookEndpointId,
)

EVENT_NAMESPACE: UUID = UUID("2f9c7a1e-5b4d-4e8f-9a36-c1d0b7e5a412")
DELIVERY_NAMESPACE: UUID = UUID("8d3e6b20-71c4-4f5a-b9e2-0a6f4c3d1e87")

# The business events each announced change may become (a booking's
# change is `booking.cancelled` when it left the booking cancelled).
EVENTS_OF_CHANGE: Mapping[LiveEventKind, tuple[BusinessEventType, ...]] = {
    LiveEventKind.BOOKING_CREATED: (BusinessEventType.BOOKING_CREATED,),
    LiveEventKind.BOOKING_CHANGED: (
        BusinessEventType.BOOKING_UPDATED,
        BusinessEventType.BOOKING_CANCELLED,
    ),
    LiveEventKind.LEAD_CREATED: (BusinessEventType.LEAD_CREATED,),
    LiveEventKind.LEAD_CHANGED: (BusinessEventType.LEAD_UPDATED,),
    LiveEventKind.HANDOFF_CREATED: (BusinessEventType.HANDOFF_CREATED,),
    LiveEventKind.HANDOFF_RESOLVED: (BusinessEventType.HANDOFF_RESOLVED,),
    LiveEventKind.CONVERSATION_STARTED: (BusinessEventType.CONVERSATION_STARTED,),
    LiveEventKind.CALL_FINISHED: (BusinessEventType.CALL_FINISHED,),
}

# Events that happen once per record: their id is derived from the record.
ONCE_PER_RECORD: frozenset[BusinessEventType] = frozenset(
    {
        BusinessEventType.BOOKING_CREATED,
        BusinessEventType.LEAD_CREATED,
        BusinessEventType.HANDOFF_CREATED,
        BusinessEventType.CONVERSATION_STARTED,
        BusinessEventType.CALL_FINISHED,
    }
)


def business_event_id(
    business_id: BusinessId, event_type: BusinessEventType, subject: str
) -> BusinessEventId:
    """
    The same id for every announcement of a once-per-record event (a
    retried job that announces a booking again), a fresh one otherwise.
    """

    if event_type not in ONCE_PER_RECORD:
        return BusinessEventId()

    return BusinessEventId(
        uuid5(EVENT_NAMESPACE, f"{business_id}\n{event_type.value}\n{subject}")
    )


def webhook_delivery_id(
    endpoint_id: WebhookEndpointId, event_id: BusinessEventId
) -> WebhookDeliveryId:
    """One delivery per endpoint and event."""

    return WebhookDeliveryId(uuid5(DELIVERY_NAMESPACE, f"{endpoint_id}\n{event_id}"))

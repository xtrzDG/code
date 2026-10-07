"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ApiKeyId(BasePrefixedTypedId):
    """Identifier of one API key of a business (Settings → Integrations)."""

    prefix = "api_key"


class BusinessEventId(BasePrefixedTypedId):
    """
    Identifier of one business event sent to webhooks (`evt_…` in other
    products): the same for every endpoint that receives it, so a receiver
    can drop a repeat. An event that happens once per thing (a booking
    made, a lead taken, a call finished) has an id derived (UUID v5) from
    its business, type and subject, so announcing it twice gives the same
    id; any other event has a random one.
    """

    prefix = "event"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class WebhookDeliveryId(BasePrefixedTypedId):
    """
    Identifier of one event's delivery to one endpoint: derived (UUID v5)
    from the endpoint and the event, so the same event never queues twice
    for an endpoint; random for a test event.
    """

    prefix = "webhook_delivery"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class WebhookEndpointId(BasePrefixedTypedId):
    """Identifier of one webhook endpoint (an address events are sent to)."""

    prefix = "webhook"


# Keep abc order for all non example types, if possible.

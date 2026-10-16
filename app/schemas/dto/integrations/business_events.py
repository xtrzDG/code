"""
The body of a webhook request: one business event in its envelope. The
`data` of each type is the same record the public API returns for it
(docs/api-versioning.md, "Webhooks").
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.integrations import BusinessEventType
from app.schemas.dto.public_api.activity import (
    PublicCall,
    PublicConversation,
    PublicHandoff,
)
from app.schemas.dto.public_api.records import PublicBooking, PublicLead
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.constrained_strings import PublicTimestamp
from app.schemas.typings.integrations.prefixed_id import (
    BusinessEventId,
    WebhookEndpointId,
)


class WebhookTestData(ImmutableDTO):
    """The data of `webhook.test`: which endpoint the owner tested."""

    endpoint_id: WebhookEndpointId


type BusinessEventData = (
    PublicBooking
    | PublicLead
    | PublicHandoff
    | PublicConversation
    | PublicCall
    | WebhookTestData
)


class BusinessEvent(ImmutableDTO):
    """
    One event as a webhook receives it: its id (the same on every attempt
    and for every endpoint: drop a repeat), its type, when it happened, the
    business and the record it is about. Events may arrive out of order.
    """

    id: BusinessEventId
    type: BusinessEventType
    created_at: PublicTimestamp
    business_id: BusinessId
    data: BusinessEventData

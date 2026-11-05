"""The sweeper of the inbox: what it found and what it asks staff to do."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.dto.handoffs import HandoffCommand
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.prefixed_id import InboundEventId


class UnansweredInboundEvent(ImmutableDTO):
    """
    A customer message the assistant gave up on (FAILED) that no person
    was asked about yet: the handoff to create (None when staff own the
    conversation already, so the event is only marked).
    """

    event_id: InboundEventId
    business_id: BusinessId
    handoff: HandoffCommand | None = None


class InboundEventHandoffMark(ImmutableDTO):
    """Staff were asked to answer this event's message."""

    event_id: InboundEventId
    business_id: BusinessId

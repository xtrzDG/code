"""A website widget message accepted for the assistant to answer."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.deliveries.prefixed_id import InboundEventId


class WidgetMessageAcceptedView(ImmutableDTO):
    """
    The visitor's message is in the inbox and a worker is answering it (202
    Accepted): the widget shows that the assistant is typing and polls
    GET .../messages until the answer, or a staff message, arrives.
    `event_id` names the message in the inbox (support and logs).
    """

    event_id: InboundEventId

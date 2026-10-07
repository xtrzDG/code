"""A website widget message accepted for the assistant to answer."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.deliveries.prefixed_id import InboundEventId


class WidgetMessageAcceptedView(ImmutableDTO):
    """
    The visitor's message is in the inbox and a worker is answering it (202
    Accepted): the widget shows that the assistant is typing until the
    answer, or a staff message, arrives. `event_id` names the message in
    the inbox (support and logs). `stream_ticket` opens the visitor's live
    stream (GET .../events?ticket=...), which says when the answer is
    ready; a widget without EventSource polls GET .../messages instead.
    """

    event_id: InboundEventId
    stream_ticket: WidgetStreamTicket | None = None

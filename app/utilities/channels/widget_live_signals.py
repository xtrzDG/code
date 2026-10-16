"""
What a website visitor's widget hears on its live stream: a worker writing
the visitor's answer (`widget.typing`) and a message for the visitor
(`widget.reply`, naming it). Both name the visitor by `WidgetVisitorId`;
other channels and the owner's test chat announce nothing here.
"""

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.channels.widget_visitors import widget_visitor_id


def announce_widget_typing(
    live_events: EventPublisherFacilitatorContract,
    business_id: BusinessId,
    channel: ChannelKind,
    channel_user_id: ChannelUserId,
) -> None:
    """A worker took the visitor's message and is writing the answer."""

    if channel is not ChannelKind.WEB_CHAT:
        return

    live_events.publish(
        business_id,
        LiveEventKind.WIDGET_TYPING,
        (widget_visitor_id(str(channel_user_id)),),
    )


def announce_widget_reply(
    live_events: EventPublisherFacilitatorContract,
    conversation: ConversationDocument,
    message_id: MessageId | None,
) -> None:
    """
    Something for the visitor of a website chat conversation: the message
    `message_id`, or (None) a turn that ended without one (staff took the
    conversation over), which the widget learns by polling once.
    """

    if conversation.channel is not ChannelKind.WEB_CHAT:
        return

    visitor = widget_visitor_id(str(conversation.channel_user_id))
    live_events.publish(
        conversation.business_id,
        LiveEventKind.WIDGET_REPLY,
        (visitor,) if message_id is None else (visitor, message_id),
        is_sandbox=conversation.is_sandbox,
    )

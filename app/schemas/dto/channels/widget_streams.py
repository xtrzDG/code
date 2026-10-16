"""
The website chat's live stream (`GET /v1/widget/{id}/events`): who may
listen (a signed ticket), what it says (typing, answers) and its limits.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import (
    WidgetStreamsPerAddress,
    WidgetStreamsPerBusiness,
)
from app.schemas.typings.channels.constrained_strings import (
    WidgetSessionKey,
    WidgetStreamTicket,
)
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.live_events.constrained_floats import (
    LiveStreamHeartbeatSeconds,
    LiveStreamLifetimeSeconds,
)


class WidgetStreamClaims(ImmutableDTO):
    """What a stream ticket says: the business, the visitor and until when."""

    business_id: BusinessId
    visitor_id: WidgetVisitorId
    expires_at: Microseconds


class WidgetStreamTicketRequest(ImmutableDTO):
    """
    A widget request that carried the visitor key (a message's body, a
    poll's header): its answer brings a ticket to the visitor's stream.
    """

    business_id: BusinessId
    session_key: WidgetSessionKey


class WidgetStreamRequest(ImmutableDTO):
    """A widget opens its visitor's stream with the ticket an answer gave it."""

    business_id: BusinessId
    ticket: WidgetStreamTicket
    client_ip_address: ClientIpAddress | None = None


class WidgetStreamGrant(ImmutableDTO):
    """An accepted ticket: the stream hears this visitor of this business."""

    business_id: BusinessId
    visitor_id: WidgetVisitorId


class WidgetStreamMessageQuery(ImmutableDTO):
    """One message a `widget.reply` event names, read for the visitor's stream."""

    business_id: BusinessId
    visitor_id: WidgetVisitorId
    message_id: MessageId


class WidgetStreamMessageView(ImmutableDTO):
    """
    An answer as the stream tells it (`answer_ready`): its id and author,
    and its text only for a model reply the reply guard passed as CLEAN (a
    draft the widget replaces with the stored text when it next polls);
    `text` None means "fetch it".
    """

    message_id: MessageId
    author: MessageAuthor
    text: MessageText | None = None
    direction: TextDirection = TextDirection.LEFT_TO_RIGHT


class WidgetStreamLimits(ImmutableDTO):
    """
    How the API keeps visitors' streams: a heartbeat comment every
    `heartbeat_seconds` of quiet, each stream ended after
    `lifetime_seconds` (the widget's EventSource reconnects with the same
    ticket), and at most `streams_per_business` and `streams_per_address`
    (one client network) open streams per API process.
    """

    heartbeat_seconds: LiveStreamHeartbeatSeconds = LiveStreamHeartbeatSeconds(20.0)
    lifetime_seconds: LiveStreamLifetimeSeconds = LiveStreamLifetimeSeconds(900.0)
    streams_per_business: WidgetStreamsPerBusiness = WidgetStreamsPerBusiness(500)
    streams_per_address: WidgetStreamsPerAddress = WidgetStreamsPerAddress(20)

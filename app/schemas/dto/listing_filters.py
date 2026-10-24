"""
What the cabinet's keyset lists filter by, as repositories receive it
(the use cases turn local dates and choices into these bounds first).
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingOrder, BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.conversations.booleans import IncludeSandboxConversations
from app.schemas.typings.users.prefixed_id import UserId


class ConversationFeedFilter(ImmutableDTO):
    """
    Conversations of the feed: in a channel, with a status, going on in a
    period (last message from `last_message_from`, started before
    `started_before`), sandbox ones only on request.
    """

    channel: ChannelKind | None = None
    status: ConversationStatus | None = None
    last_message_from: Microseconds | None = None
    started_before: Microseconds | None = None
    include_sandbox: IncludeSandboxConversations = False


class BookingListFilter(ImmutableDTO):
    """
    Bookings starting from `starts_from` (inclusive) to `starts_before`
    (exclusive), with a status and on a resource, earliest or latest first.
    """

    starts_from: BookingSearchBoundSeconds | None = None
    starts_before: BookingSearchBoundSeconds | None = None
    status: BookingStatus | None = None
    resource_id: ResourceId | None = None
    include_sandbox: IsSandboxIncluded = False
    order: BookingOrder = BookingOrder.EARLIEST_FIRST


class HandoffListFilter(ImmutableDTO):
    """Handoffs with one status (any without), sandbox ones on request."""

    status: HandoffStatus | None = None
    include_sandbox: IsSandboxIncluded = False


class AuditLogFilter(ImmutableDTO):
    """Audit entries of one operation, entity type and person in a period."""

    action: AuditAction | None = None
    entity: AuditEntityName | None = None
    actor_id: UserId | None = None
    since: Microseconds | None = None
    until: Microseconds | None = None

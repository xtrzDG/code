"""
The team inbox: one view of a business's conversations, its counts, and
the staff-safe row of a conversation.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.constants.inbox import InboxView
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsAfterHours
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessagePreview
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.inbox.booleans import (
    AwaitsTeam,
    HasOpenRequest,
    IsAssignedAutomatically,
    NeedsPerson,
)
from app.schemas.typings.inbox.constrained_integers import (
    AssignmentRevision,
    AwaitingConversationCount,
    ConversationNoteCount,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName


class InboxViewFilter(ImmutableDTO):
    """Which conversations a view shows: `viewer` is "me" of MINE."""

    view: InboxView
    viewer: UserId
    channel: ChannelKind | None = None


class InboxQuery(ImmutableDTO):
    """
    One page of a view of the team inbox, the latest message first, with
    the counts of the views. The page is written to the audit log as the
    viewer's view of the inbox.
    """

    user_id: UserId
    business_id: BusinessId
    view: InboxView = InboxView.ALL
    channel: ChannelKind | None = None
    page: PageRequest = Field(default_factory=PageRequest)
    client_ip_address: ClientIpAddress | None = None


class InboxViewCounts(ImmutableDTO):
    """
    How many conversations each view holds (sandbox left out): those that
    need a person, have an open request, wait for the team and are assigned
    to the viewer, and wait for the team with nobody assigned. "All" has no
    count: it is the whole history.
    """

    needs_person: ListItemCount = ListItemCount(0)
    requests: ListItemCount = ListItemCount(0)
    mine: ListItemCount = ListItemCount(0)
    unassigned: ListItemCount = ListItemCount(0)


class InboxHandoffSummary(ImmutableDTO):
    """The open handoff of a conversation, as the inbox row shows it."""

    id: HandoffId
    reason: HandoffReason
    urgency: HandoffUrgency
    status: HandoffStatus
    created_at: Microseconds


class InboxRequestSummary(ImmutableDTO):
    """The newest open request of a conversation (no free-text details)."""

    id: LeadId
    lead_type: LeadType
    status: LeadStatus
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    created_at: Microseconds


class InboxItemView(ImmutableDTO):
    """
    A conversation row of the team inbox, safe for every staff member:
    who the customer is, where and how the conversation stands, who is
    assigned, the beginning of the last message and what waits (the open
    handoff, the newest open request). No model, cost or tool details,
    no free-text request details and no note texts (only their count).
    `assignment_revision` is what an assignment must name.
    """

    id: ConversationId
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    channel: ChannelKind
    language: LanguageTag | None = None
    status: ConversationStatus
    is_after_hours: IsAfterHours
    needs_person: NeedsPerson
    has_open_request: HasOpenRequest
    awaits_team: AwaitsTeam
    assignee_user_id: UserId | None = None
    assigned_at: Microseconds | None = None
    is_assigned_automatically: IsAssignedAutomatically = False
    assignment_revision: AssignmentRevision
    last_message_text: MessagePreview | None = None
    last_message_author: MessageAuthor | None = None
    last_message_at: Microseconds
    created_at: Microseconds
    note_count: ConversationNoteCount = ConversationNoteCount(0)
    handoff: InboxHandoffSummary | None = None
    request: InboxRequestSummary | None = None


class InboxItemSource(ImmutableDTO):
    """A conversation with what its inbox row is built from."""

    conversation: ConversationDocument
    contact: ContactDocument | None = None
    last_written: MessageDocument | None = None
    note_count: ConversationNoteCount = ConversationNoteCount(0)
    handoff: HandoffDocument | None = None
    request: LeadDocument | None = None


class InboxPage(ImmutableDTO):
    """One page of a view; `next_cursor` is None on the last page."""

    view: InboxView
    items: list[InboxItemView] = Field(default_factory=list[InboxItemView])
    counts: InboxViewCounts = Field(default_factory=InboxViewCounts)
    next_cursor: PageCursor | None = None


class InboxAssigneesQuery(ImmutableDTO):
    """The members a conversation can be assigned to."""

    user_id: UserId
    business_id: BusinessId


class InboxAssigneeView(ImmutableDTO):
    """
    A member of the business to assign conversations to, with how many
    conversations waiting for the team they have now (no phone or e-mail).
    """

    user_id: UserId
    display_name: UserDisplayName | None = None
    role: BusinessMemberRole
    awaiting_count: AwaitingConversationCount = AwaitingConversationCount(0)


class InboxAssigneeList(ImmutableDTO):
    """The members of the business, owners first, then by name."""

    items: list[InboxAssigneeView] = Field(default_factory=list[InboxAssigneeView])

"""Leads in the cabinet: the list with status counts and status changes."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.bookings.strings import LeadBudgetText, LeadDetails
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class ListLeadsQuery(ImmutableDTO):
    """One page of the leads of a business for the cabinet, newest first."""

    business_id: BusinessId
    actor_id: UserId
    client_ip_address: ClientIpAddress | None = None
    status: LeadStatus | None = None
    include_sandbox: IsSandboxIncluded = False
    page: PageRequest = PageRequest()


class LeadListItem(ImmutableDTO):
    """Lead with the contact it came from."""

    id: LeadId
    business_id: BusinessId
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    conversation_id: ConversationId | None = None
    lead_type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    source_channel: ChannelKind
    status: LeadStatus
    is_sandbox: IsSandboxConversation = False
    created_at: Microseconds


class LeadStatusCount(ImmutableDTO):
    """How many leads have one status (for the status tabs)."""

    status: LeadStatus
    count: ListItemCount


class LeadPage(ImmutableDTO):
    """
    One page of leads, newest first, and how many leads of each status
    there are (the status filter aside), for the tabs.
    """

    items: list[LeadListItem] = Field(default_factory=list[LeadListItem])
    next_cursor: PageCursor | None = None
    status_counts: list[LeadStatusCount] = Field(default_factory=list[LeadStatusCount])


class UpdateLeadStatusRequest(ImmutableDTO):
    """Body of a cabinet lead status change."""

    status: LeadStatus


class UpdateLeadStatusCommand(ImmutableDTO):
    """Staff moves a lead through NEW, IN_PROGRESS, WON or LOST."""

    business_id: BusinessId
    lead_id: LeadId
    status: LeadStatus

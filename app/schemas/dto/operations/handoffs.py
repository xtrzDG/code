"""
Handoffs in the cabinet: the list and resolving a handoff.

Model-tool DTOs (handoff to a human) live in `app/schemas/dto/handoffs.py`.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffStatus,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.handoffs.booleans import IsHandoffOpen
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.handoffs.strings import HandoffQuotedText, HandoffSummary
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class ListHandoffsQuery(ImmutableDTO):
    """
    One page of the handoffs of a business for the cabinet.

    `is_open` True keeps the ones still waiting for a person (any status but
    RESOLVED), False the resolved ones. Open handoffs come first, the most
    urgent first, then the one waiting longest; resolved ones follow, the
    most recently resolved first.
    """

    business_id: BusinessId
    actor_id: UserId
    status: HandoffStatus | None = None
    is_open: IsHandoffOpen | None = None
    include_sandbox: IsSandboxIncluded = False
    page: PageRequest = PageRequest()


class HandoffListItem(ImmutableDTO):
    """
    Handoff with the contact to call back.

    When `summary_code` is set the platform created the handoff: the
    cabinet shows the code from its own dictionary in the reader's
    language, with `quoted_text` and `flagged_values`; `summary` is the
    same in the business's staff language. Otherwise `summary` is the
    model's own.
    """

    id: HandoffId
    business_id: BusinessId
    conversation_id: ConversationId
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    reason: HandoffReason
    summary: HandoffSummary
    summary_code: HandoffSummaryCode | None = None
    quoted_text: HandoffQuotedText | None = None
    flagged_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    urgency: HandoffUrgency
    status: HandoffStatus
    is_sandbox: IsSandboxConversation = False
    created_at: Microseconds
    resolved_at: Microseconds | None = None


class HandoffPage(ImmutableDTO):
    """
    One page of handoffs and how many are open and resolved (the status
    filters aside), for the tabs.
    """

    items: list[HandoffListItem] = Field(default_factory=list[HandoffListItem])
    next_cursor: PageCursor | None = None
    open_count: ListItemCount
    resolved_count: ListItemCount


class ResolveHandoffCommand(ImmutableDTO):
    """Staff closes a handoff; the assistant may answer the conversation again."""

    business_id: BusinessId
    handoff_id: HandoffId

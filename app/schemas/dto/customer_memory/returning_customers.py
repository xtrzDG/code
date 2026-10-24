"""What the assistant knows of a customer who comes back."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.bookings import BookingView, LeadView
from app.schemas.typings.conversations.booleans import (
    CarriesCustomerMemory,
    IsNewConversation,
)
from app.schemas.typings.conversations.constrained_integers import (
    EarlierConversationCount,
)
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText


class RememberedConversation(ImmutableDTO):
    """An earlier conversation of the customer and what it was about."""

    last_message_at: Microseconds
    channel: ChannelKind
    summary: ConversationSummaryText


class RememberedNote(ImmutableDTO):
    """An internal note of the team on one of the customer's conversations."""

    created_at: Microseconds
    text: ConversationNoteText


class ReturningCustomerContext(ImmutableDTO):
    """
    The memory of one customer of one business, never of another: how many
    conversations they had before this one and when the last was, what the
    latest ones were about (up to three summaries), their bookings still to
    come, their requests staff have not closed and, when the owner allows
    it, the team's notes on their latest conversations.
    """

    earlier_conversation_count: EarlierConversationCount = EarlierConversationCount(0)
    last_visit_at: Microseconds | None = None
    summaries: list[RememberedConversation] = Field(
        default_factory=list[RememberedConversation]
    )
    upcoming_bookings: list[BookingView] = Field(default_factory=list[BookingView])
    open_leads: list[LeadView] = Field(default_factory=list[LeadView])
    team_notes: list[RememberedNote] = Field(default_factory=list[RememberedNote])

    @property
    def is_empty(self) -> bool:
        """Nothing to remember: a first-time customer without bookings."""

        return (
            int(self.earlier_conversation_count) == 0
            and not self.upcoming_bookings
            and not self.open_leads
        )


class CustomerMemoryRequest(ImmutableDTO):
    """
    One customer message's turn, for the memory: the conversation as found
    (before the message touched it, `previous_last_message_at` None for a
    new one) and whether this turn opens the assistant's part of it, the
    only turn whose user message carries the memory.
    """

    business: BusinessDocument
    contact: ContactDocument
    conversation: ConversationDocument
    is_new_conversation: IsNewConversation
    previous_last_message_at: Microseconds | None = None
    wants_context: CarriesCustomerMemory
    now: Microseconds


class CustomerMemory(ImmutableDTO):
    """The memory to add to the turn; None when there is nothing or it is off."""

    context: ReturningCustomerContext | None = None

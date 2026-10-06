"""One keyset page of a business's records through the public API."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.dto.public_api.activity import PublicConversation
from app.schemas.dto.public_api.records import (
    PublicBooking,
    PublicContact,
    PublicLead,
)
from app.schemas.typings.platform.constrained_strings import PageCursor


class PublicBookingPage(ImmutableDTO):
    """Bookings, the latest start first."""

    items: list[PublicBooking] = Field(default_factory=list[PublicBooking])
    next_cursor: PageCursor | None = None


class PublicLeadPage(ImmutableDTO):
    """Leads, the newest first."""

    items: list[PublicLead] = Field(default_factory=list[PublicLead])
    next_cursor: PageCursor | None = None


class PublicContactPage(ImmutableDTO):
    """Contacts, the newest first (erased ones are left out)."""

    items: list[PublicContact] = Field(default_factory=list[PublicContact])
    next_cursor: PageCursor | None = None


class PublicConversationPage(ImmutableDTO):
    """Conversations, the latest message first (no test chats)."""

    items: list[PublicConversation] = Field(default_factory=list[PublicConversation])
    next_cursor: PageCursor | None = None

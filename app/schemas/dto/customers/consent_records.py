"""Where a change of a customer's marketing consent came from (the ledger)."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.consent_records import ConsentEventSource
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class ConsentOrigin(ImmutableDTO):
    """
    The circumstances of a consent's change, as the consent ledger keeps
    them: where (`source`) and its reference (`booking_id` of the page,
    `conversation_id` of a STOP's chat), the chat it covers or came from,
    the language its wording was shown in, the team member who recorded it
    (None: the customer or the platform) and the client's network.
    """

    source: ConsentEventSource
    channel: ChannelKind | None = None
    language: LanguageTag | None = None
    recorded_by: UserId | None = None
    booking_id: BookingId | None = None
    conversation_id: ConversationId | None = None
    client_ip_address: ClientIpAddress | None = None

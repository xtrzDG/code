from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.consent_records import (
    ConsentEvent,
    ConsentEventSource,
    ConsentPurpose,
)
from app.schemas.constants.marketing_consent import MarketingConsentText
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ConsentRecordId, ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class ConsentRecordDocument(BaseDocument):
    """
    One entry of a business's consent ledger (migration 1240): a customer
    gave (`GIVEN`) or took back (`WITHDRAWN`) their consent for `purpose`,
    at `created_at` (UTC microseconds). Append-only: an entry is never
    changed or deleted (the database refuses it to the application's
    tenant role); only the deletion of the whole business removes the
    business's ledger.

    What the entry proves (GDPR art. 7(1)): the customer (`contact_id`),
    where it happened (`source`: the booking's page, the team in person, a
    STOP, the erasure) and its reference (`booking_id` of the page,
    `conversation_id` of the chat a STOP came in), the chat it covers or
    came from (`channel`), the exact wording (`text_version`) and the
    language it was shown in (`language`), who recorded it (`recorded_by`,
    the team member; None: the customer themselves or the platform) and
    the client's network (`client_ip_address`, when the customer acted on
    a page).

    The ledger outlives the customer's erasure as pseudonymous proof: it
    names the contact only by its id (an erased contact keeps only that)
    and holds no name, number, account or words of theirs.
    """

    id: ConsentRecordId = Field(default_factory=ConsentRecordId)
    business_id: BusinessId
    contact_id: ContactId
    purpose: ConsentPurpose = ConsentPurpose.MARKETING
    event: ConsentEvent
    source: ConsentEventSource
    channel: ChannelKind | None = None
    text_version: MarketingConsentText | None = None
    language: LanguageTag | None = None
    recorded_by: UserId | None = None
    booking_id: BookingId | None = None
    conversation_id: ConversationId | None = None
    client_ip_address: ClientIpAddress | None = None

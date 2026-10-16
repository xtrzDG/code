from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)


class MissedCallDocument(BaseDocument):
    """
    A call whose caller did not get through (no answer, busy, hung up
    before the assistant, a failed start, a transfer nobody picked up) and
    the message that tells them the business will continue in writing
    (the text-back).

    The id derives from the business, the source and the provider's call
    id, so a repeated report is the same missed call and is texted once.
    `language` is the caller's (detected on the call) or their country's
    when the business speaks it. A WhatsApp text-back opens the
    conversation (`conversation_id`) the caller's reply continues in.
    Rows are purged after 90 days.
    """

    id: MissedCallId
    business_id: BusinessId
    source: MissedCallSource
    provider_call_id: ProviderCallId
    reason: MissedCallReason
    caller_phone_number: E164PhoneNumber | None = None
    called_at: Microseconds
    language: LanguageTag
    call_id: CallId | None = None
    status: TextBackStatus
    skip_reason: TextBackSkipReason | None = None
    channel: TextBackChannel | None = None
    conversation_id: ConversationId | None = None
    sent_at: Microseconds | None = None
    last_error: DeliveryErrorText | None = None

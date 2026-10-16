"""
A visitor's traces outside their conversations, for the data-rights tests:
the business's Telegram channel, a missed call from the visitor's number,
a reminder still waiting in the outbox, a message they sent through a
webhook, and a request for feedback after their visit.
"""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackStatus,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.deliveries import (
    InboundEventKind,
    InboundEventStatus,
    OutboundMessageKind,
)
from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
)
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    MessageText,
    ProviderCallId,
)
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.deliveries.prefixed_id import (
    InboundEventId,
    OutboundMessageId,
)
from app.schemas.typings.feedback.constrained_integers import VisitScore
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.feedback.prefixed_id import FeedbackRequestId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.deliveries.delivery_keys import customer_recipient_key
from tests.compliance.visitor_records import SeededVisitor
from tests.users.accounts_testbed import AccountsTestbed


@dataclass(frozen=True)
class VisitorTraces:
    missed_call: MissedCallDocument
    reminder: OutboundMessageDocument
    inbound_event: InboundEventDocument
    feedback_request: FeedbackRequestDocument


def derived(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, name))


def seed_traces(
    testbed: AccountsTestbed, visitor: SeededVisitor, name: str
) -> VisitorTraces:
    """The traces of one seeded visitor (its Telegram chat and its phone)."""

    business_id = visitor.contact.business_id
    now: Microseconds = testbed.clock.now_microseconds()
    channels = testbed.channel_repo.list_by_business(business_id)
    channel = next(
        (item for item in channels if item.kind is ChannelKind.TELEGRAM), None
    ) or ChannelDocument(
        business_id=business_id,
        kind=ChannelKind.TELEGRAM,
        status=ChannelStatus.CONNECTED,
        created_at=now,
        updated_at=now,
    )
    testbed.channel_repo.save(channel)
    account = visitor.chat_conversation.channel_user_id
    phone = visitor.contact.phone_number
    assert phone is not None
    missed_call = MissedCallDocument(
        id=MissedCallId(derived(f"missed:{name}")),
        business_id=business_id,
        source=MissedCallSource.PBX,
        provider_call_id=ProviderCallId(f"pbx-{visitor.contact.id}"),
        reason=MissedCallReason.NO_ANSWER,
        caller_phone_number=E164PhoneNumber(str(phone)),
        called_at=now,
        language=LanguageTag("ka"),
        status=TextBackStatus.SENT,
        created_at=now,
        updated_at=now,
    )
    testbed.missed_call_repo.insert_if_new(missed_call)
    reminder = OutboundMessageDocument(
        id=OutboundMessageId(derived(f"reminder:{name}")),
        business_id=business_id,
        kind=OutboundMessageKind.BOOKING_REMINDER,
        idempotency_key=OutboundIdempotencyKey(f"reminder:{visitor.booking.id}"),
        recipient_key=customer_recipient_key(channel.id, account),
        customer=CustomerRecipient(
            channel_id=channel.id,
            channel=ChannelKind.TELEGRAM,
            channel_user_id=account,
        ),
        text=MessageText(f"{name}, see you tomorrow at 19:00"),
        booking_id=visitor.booking.id,
        created_at=now,
        updated_at=now,
    )
    testbed.outbound_message_repo.insert_if_new(reminder)
    inbound_event = InboundEventDocument(
        id=InboundEventId(derived(f"inbound:{name}")),
        business_id=business_id,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=ChannelKind.TELEGRAM,
        channel_id=channel.id,
        provider_message_id=ProviderMessageId(f"tg-{visitor.contact.id}"),
        customer_message=InboundCustomerMessage(
            channel_user_id=ChannelUserId(str(account)),
            text=MessageText(f"Hi, this is {name}, call me on {phone}"),
            contact_name=ContactName(name),
            contact_phone_number=E164PhoneNumber(str(phone)),
        ),
        status=InboundEventStatus.RECEIVED,
        created_at=now,
        updated_at=now,
    )
    testbed.inbound_event_repo.insert_if_new(inbound_event)
    feedback_request = FeedbackRequestDocument(
        id=FeedbackRequestId(derived(f"feedback:{name}")),
        business_id=business_id,
        booking_id=visitor.booking.id,
        contact_id=visitor.contact.id,
        visit_ended_at=now,
        language=LanguageTag("ka"),
        status=FeedbackRequestStatus.ANSWERED,
        channel=ChannelKind.TELEGRAM,
        review_token=ReviewLinkToken(f"{name}-review-token-0000000"[:22]),
        score=VisitScore(5),
        created_at=now,
        updated_at=now,
    )
    testbed.feedback_request_repo.insert_if_new(feedback_request)
    return VisitorTraces(missed_call, reminder, inbound_event, feedback_request)

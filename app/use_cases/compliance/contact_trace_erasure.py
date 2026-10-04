"""
Erasing a visitor's traces outside their conversations (missed calls,
queued messages, webhook events, requests for feedback). The records stay
for the business's counts; what identifies the person or repeats their
words goes. Each change is one atomic update of the stored row, so a
worker handling the row at the same time cannot write the old text back.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.call_follow_up_repositories import (
    MissedCallRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    InboundEventRepoContract,
    OutboundMessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.schemas.constants.deliveries import InboundEventStatus, OutboundMessageStatus
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.compliance import ContactRecords
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundRecipientKey
from app.schemas.typings.deliveries.strings import DeliveryErrorText, InboundErrorText

ERASED_TEXT: str = "[erased at the visitor's request]"
ERASED_ACCOUNT_PREFIX: str = "erased-"
UNPROCESSED_EVENTS: frozenset[InboundEventStatus] = frozenset(
    {InboundEventStatus.RECEIVED, InboundEventStatus.PROCESSING}
)


@dataclass(frozen=True)
class TraceErasure:
    missed_calls: ErasedRecordCount
    outbound_messages: ErasedRecordCount
    inbound_events: ErasedRecordCount
    feedback_requests: ErasedRecordCount


@dataclass(frozen=True)
class ContactTraceEraser:
    missed_call_repo: MissedCallRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    inbound_event_repo: InboundEventRepoContract
    feedback_request_repo: FeedbackRequestRepoContract

    def erase(self, records: ContactRecords, now: Microseconds) -> TraceErasure:
        business_id = records.contact.business_id
        for missed_call in records.missed_calls:
            self.missed_call_repo.update(
                business_id,
                missed_call.id,
                lambda stored: erase_missed_call(stored, now),
            )

        for message in records.outbound_messages:
            self.outbound_message_repo.update(
                business_id, message.id, lambda stored: erase_outbound(stored, now)
            )

        for event in records.inbound_events:
            self.inbound_event_repo.update(
                business_id, event.id, lambda stored: erase_inbound(stored, now)
            )

        for request in records.feedback_requests:
            self.feedback_request_repo.update(
                business_id, request.id, lambda stored: erase_feedback(stored, now)
            )

        return TraceErasure(
            missed_calls=ErasedRecordCount(len(records.missed_calls)),
            outbound_messages=ErasedRecordCount(len(records.outbound_messages)),
            inbound_events=ErasedRecordCount(len(records.inbound_events)),
            feedback_requests=ErasedRecordCount(len(records.feedback_requests)),
        )


def erase_missed_call(
    missed_call: MissedCallDocument, now: Microseconds
) -> MissedCallDocument:
    """The call stays counted; the caller's number (and errors naming it) go."""

    missed_call.caller_phone_number = None
    missed_call.last_error = None
    missed_call.updated_at = now
    return missed_call


def erase_outbound(
    message: OutboundMessageDocument, now: Microseconds
) -> OutboundMessageDocument:
    """
    The text, template parameters and the account go; a message still
    waiting is given up, so nothing more reaches the erased visitor.
    """

    erased_account = ChannelUserId(f"{ERASED_ACCOUNT_PREFIX}{message.id}")
    message.text = MessageText(ERASED_TEXT)
    if message.template is not None:
        message.template.body_parameters = []

    if message.customer is not None:
        message.customer.channel_user_id = erased_account
        message.recipient_key = OutboundRecipientKey(
            f"customer:{message.customer.channel_id}:{erased_account}"
        )

    if message.status is OutboundMessageStatus.PENDING:
        message.status = OutboundMessageStatus.DEAD
        message.next_attempt_at = None

    message.last_error = DeliveryErrorText(ERASED_TEXT)
    message.updated_at = now
    return message


def erase_inbound(
    event: InboundEventDocument, now: Microseconds
) -> InboundEventDocument:
    """
    The visitor's words, name, number, files and account go, and so does a
    platform payload; an event not processed yet is not processed anymore.
    """

    erased_account = ChannelUserId(f"{ERASED_ACCOUNT_PREFIX}{event.id}")
    if event.customer_message is not None:
        event.customer_message = InboundCustomerMessage(
            channel_user_id=erased_account, text=MessageText(ERASED_TEXT)
        )
        event.customer_channel_user_id = erased_account

    event.payload = None
    event.last_error = InboundErrorText(ERASED_TEXT)
    if event.status in UNPROCESSED_EVENTS:
        event.status = InboundEventStatus.FAILED
        event.lease_until = None

    event.updated_at = now
    return event


def erase_feedback(
    request: FeedbackRequestDocument, now: Microseconds
) -> FeedbackRequestDocument:
    """The rating stays in the business's statistics; the review link goes."""

    request.review_token = None
    request.last_error = None
    request.updated_at = now
    return request

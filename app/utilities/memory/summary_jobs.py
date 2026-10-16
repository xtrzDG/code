"""
The job that writes a conversation's summary, its payload, and when it is
due: two hours after the conversation's latest message.
"""

from pydantic import ValidationError
from typed_time_provider import Microseconds

from app.schemas.dto.customer_memory.conversation_summaries import (
    SummaryJobPayload,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson

SUMMARIZE_CONVERSATION_JOB: JobName = JobName("summarize_conversation")
# A conversation quiet this long is over for now: its summary is written.
SUMMARY_IDLE_MICROSECONDS: int = 2 * 60 * 60 * 1_000_000


def encode_summary_payload(conversation_id: ConversationId) -> JobPayloadJson:
    return JobPayloadJson(
        SummaryJobPayload(conversation_id=conversation_id).model_dump_json()
    )


def decode_summary_payload(payload: JobPayloadJson) -> ConversationId:
    try:
        return SummaryJobPayload.model_validate_json(str(payload)).conversation_id
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload does not name a conversation."
        ) from error


def summary_due_at(last_message_at: Microseconds) -> Microseconds:
    """When a conversation whose latest message came then is quiet enough."""

    return Microseconds(int(last_message_at) + SUMMARY_IDLE_MICROSECONDS)


def starts_active_period(
    previous_last_message_at: Microseconds | None,
    now: Microseconds,
) -> bool:
    """
    A message in a new conversation, or after two quiet hours, starts a new
    active period of it: the one moment its summary job is queued (the job
    moves itself later while messages keep coming).
    """

    return (
        previous_last_message_at is None
        or int(now) - int(previous_last_message_at) >= SUMMARY_IDLE_MICROSECONDS
    )

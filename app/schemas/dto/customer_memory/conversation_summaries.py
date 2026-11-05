"""The summary of one conversation and the job that writes it."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId


class ConversationSummaryWrite(ImmutableDTO):
    """
    A summary to store: written at `written_at` from the conversation as it
    was with its latest message at `covers_until`.
    """

    summary: ConversationSummaryText
    written_at: Microseconds
    covers_until: Microseconds


class SummaryJobPayload(ImmutableDTO):
    """The queued job's payload: the conversation to summarize once it is quiet."""

    conversation_id: ConversationId

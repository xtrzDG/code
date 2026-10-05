"""
Deleting the copies the sub-processors keep (Langfuse traces, ElevenLabs
call records) when the platform deletes its own: what one deletion covers,
and the payload of its queued job.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.privacy import ProcessorErasureReason, SubProcessor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ProviderCallId


class ProcessorErasureScope(ImmutableDTO):
    """
    The records of one business whose copies at the sub-processors go:
    conversations (the sessions of their model-call traces) and calls (the
    voice platform's conversation ids).
    """

    business_id: BusinessId
    reason: ProcessorErasureReason
    conversation_ids: list[ConversationId] = Field(default_factory=list[ConversationId])
    provider_call_ids: list[ProviderCallId] = Field(
        default_factory=list[ProviderCallId]
    )

    def is_empty(self) -> bool:
        return not self.conversation_ids and not self.provider_call_ids


class ProcessorErasureJobPayload(ImmutableDTO):
    """
    The queued job "erase_processor_copies": the copies one sub-processor
    keeps of a batch of conversations or calls (the job names the business).
    """

    processor: SubProcessor
    reason: ProcessorErasureReason
    conversation_ids: list[ConversationId] = Field(default_factory=list[ConversationId])
    provider_call_ids: list[ProviderCallId] = Field(
        default_factory=list[ProviderCallId]
    )

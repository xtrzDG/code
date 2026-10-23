"""
What the model and the voice platform keep of a deleted business's
conversations: the raw model turns (a platform collection keyed by
conversation) go here, the copies at the sub-processors by queued jobs.
"""

from app.contracts.knowledge_embeddings import KnowledgeEmbeddingStoreContract
from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.contracts.repositories.conversation_repositories import LlmTurnRepoContract
from app.schemas.constants.privacy import ProcessorErasureReason
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.privacy.constrained_integers import ProcessorErasureJobCount
from app.use_cases.shared.document_pages import pages_in_write_order

# A business's deletion is the retention clause of the DPA (13.3), so its
# sub-processor jobs carry the retention reason the release before this one
# already reads.
DELETION_REASON: ProcessorErasureReason = ProcessorErasureReason.RETENTION


class ConversationTraceEraser:
    """
    Page by page over the business's conversations and calls: their model
    turns are deleted, and the sub-processors that keep copies (the model
    calls' traces at Langfuse, the calls at ElevenLabs) get erasure jobs
    with retries (`ProcessorErasureFacilitatorContract`), so an outage
    there never holds the deletion up and never loses it. The knowledge's
    search vectors go too (pgvector rows of the business).
    """

    def __init__(
        self,
        conversations: BusinessDocumentPagesContract[ConversationDocument],
        calls: BusinessDocumentPagesContract[CallDocument],
        knowledge_items: BusinessDocumentPagesContract[KnowledgeItemDocument],
        llm_turn_repo: LlmTurnRepoContract,
        embedding_store: KnowledgeEmbeddingStoreContract,
        processor_erasure: ProcessorErasureFacilitatorContract,
    ) -> None:
        self._conversations: BusinessDocumentPagesContract[ConversationDocument] = (
            conversations
        )
        self._calls: BusinessDocumentPagesContract[CallDocument] = calls
        self._knowledge_items: BusinessDocumentPagesContract[KnowledgeItemDocument] = (
            knowledge_items
        )
        self._llm_turn_repo: LlmTurnRepoContract = llm_turn_repo
        self._embedding_store: KnowledgeEmbeddingStoreContract = embedding_store
        self._processor_erasure: ProcessorErasureFacilitatorContract = processor_erasure

    def erase(self, business_id: BusinessId) -> ProcessorErasureJobCount:
        """Delete the model turns and vectors; how many erasure jobs were queued."""

        queued: int = 0
        for page in pages_in_write_order(
            self._conversations, business_id, lambda item: str(item.id)
        ):
            for conversation in page:
                self._llm_turn_repo.delete_by_conversation(conversation.id)
            queued += int(
                self._processor_erasure.request_erasure(
                    ProcessorErasureScope(
                        business_id=business_id,
                        reason=DELETION_REASON,
                        conversation_ids=[conversation.id for conversation in page],
                    )
                )
            )

        for calls in pages_in_write_order(
            self._calls, business_id, lambda item: str(item.id)
        ):
            provider_call_ids: list[ProviderCallId] = [
                call.provider_call_id for call in calls
            ]
            queued += int(
                self._processor_erasure.request_erasure(
                    ProcessorErasureScope(
                        business_id=business_id,
                        reason=DELETION_REASON,
                        provider_call_ids=provider_call_ids,
                    )
                )
            )

        for items in pages_in_write_order(
            self._knowledge_items, business_id, lambda item: str(item.id)
        ):
            self._embedding_store.delete(business_id, [item.id for item in items])

        return ProcessorErasureJobCount(queued)

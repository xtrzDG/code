from app.contracts.channel_clients import ElevenLabsApiClientContract
from app.contracts.processor_erasure import ProcessorErasureAdapterContract
from app.schemas.constants.privacy import SubProcessor
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount


class ElevenLabsConversationErasureAdapter(ProcessorErasureAdapterContract):
    """
    ElevenLabs keeps each call it handled as a conversation (the audio, the
    transcript, the analysis), under the id the platform stores as the
    call's `provider_call_id`. Deleting a call's copies deletes that
    conversation (DELETE /v1/convai/conversations/{id}); one gone already
    (the recording was archived, or an earlier try got through) counts as
    deleted.
    """

    def __init__(self, client: ElevenLabsApiClientContract) -> None:
        self._client: ElevenLabsApiClientContract = client

    @property
    def processor(self) -> SubProcessor:
        return SubProcessor.ELEVENLABS

    @property
    def deletes_copies(self) -> bool:
        return True

    def copies_in(self, scope: ProcessorErasureScope) -> ProcessorErasureScope | None:
        if not scope.provider_call_ids:
            return None

        return scope.model_copy(update={"conversation_ids": []})

    def erase(self, scope: ProcessorErasureScope) -> ErasedRecordCount:
        for provider_call_id in scope.provider_call_ids:
            self._client.delete_conversation(provider_call_id)

        return ErasedRecordCount(len(scope.provider_call_ids))

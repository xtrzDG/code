from app.contracts.processor_erasure import (
    LangfuseTraceClientContract,
    ProcessorErasureAdapterContract,
)
from app.schemas.constants.privacy import SubProcessor
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.schemas.typings.platform.strings import CorrelationId, TraceSessionId

# Trace ids one DELETE request names.
DELETE_BATCH_SIZE: int = 100


class LangfuseTraceErasureAdapter(ProcessorErasureAdapterContract):
    """
    Langfuse keeps a trace of every model call (the quality journal); the
    traces of a conversation share its id as their `sessionId`
    (`langfuse_trace_facilitator`). Deleting a conversation's copies lists
    the session's traces and deletes them by id; Langfuse removes them in
    the background. Its project retention (30 days, docs/LAUNCH.md) deletes
    whatever is left on its own.
    """

    def __init__(self, client: LangfuseTraceClientContract) -> None:
        self._client: LangfuseTraceClientContract = client

    @property
    def processor(self) -> SubProcessor:
        return SubProcessor.LANGFUSE

    @property
    def deletes_copies(self) -> bool:
        return True

    def copies_in(self, scope: ProcessorErasureScope) -> ProcessorErasureScope | None:
        if not scope.conversation_ids:
            return None

        return scope.model_copy(update={"provider_call_ids": []})

    def erase(self, scope: ProcessorErasureScope) -> ErasedRecordCount:
        deleted: int = 0
        for conversation_id in scope.conversation_ids:
            trace_ids: list[CorrelationId] = self._client.list_session_trace_ids(
                TraceSessionId(str(conversation_id))
            )
            for start in range(0, len(trace_ids), DELETE_BATCH_SIZE):
                batch: list[CorrelationId] = trace_ids[
                    start : start + DELETE_BATCH_SIZE
                ]
                self._client.delete_traces(batch)
                deleted += len(batch)

        return ErasedRecordCount(deleted)

from collections.abc import Sequence

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.processor_erasure import (
    ProcessorErasureAdapterContract,
    ProcessorErasureFacilitatorContract,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.privacy import SubProcessor
from app.schemas.dto.processor_erasure import (
    ProcessorErasureJobPayload,
    ProcessorErasureScope,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.privacy.constrained_integers import ProcessorErasureJobCount
from app.utilities.privacy.processor_erasure_jobs import (
    ERASE_PROCESSOR_COPIES_JOB,
    split_scope,
)


class ProcessorErasureFacilitator(ProcessorErasureFacilitatorContract):
    """
    The deletion of copies at the sub-processors, through the job queue:
    each processor that keeps copies of a scope gets its own jobs (up to
    100 conversations or calls each), retried with backoff until the
    processor answers, so an outage at Langfuse or ElevenLabs never fails
    the erasure or the purge that asked for it, and never loses the
    deletion either. A processor that cannot delete anything (Meta,
    Telegram) gets no job.
    """

    def __init__(
        self,
        adapters: Sequence[ProcessorErasureAdapterContract],
        job_queue: JobQueueFacilitatorContract,
    ) -> None:
        self._adapters: dict[SubProcessor, ProcessorErasureAdapterContract] = {
            adapter.processor: adapter for adapter in adapters
        }
        self._job_queue: JobQueueFacilitatorContract = job_queue

    def request_erasure(self, scope: ProcessorErasureScope) -> ProcessorErasureJobCount:
        queued: int = 0
        for adapter in self._adapters.values():
            copies: ProcessorErasureScope | None = adapter.copies_in(scope)
            if copies is None or copies.is_empty():
                continue

            for batch in split_scope(copies):
                payload = ProcessorErasureJobPayload(
                    processor=adapter.processor,
                    reason=batch.reason,
                    conversation_ids=batch.conversation_ids,
                    provider_call_ids=batch.provider_call_ids,
                )
                self._job_queue.enqueue(
                    ERASE_PROCESSOR_COPIES_JOB,
                    JobPayloadJson(payload.model_dump_json()),
                    business_id=scope.business_id,
                    lane=JobLane.DEFAULT,
                )
                queued += 1

        return ProcessorErasureJobCount(queued)

    def erase(
        self, processor: SubProcessor, scope: ProcessorErasureScope
    ) -> ErasedRecordCount:
        adapter: ProcessorErasureAdapterContract | None = self._adapters.get(processor)
        if adapter is None:
            # The processor was configured when the job was queued and is
            # not anymore: nothing can be sent to it, so nothing is retried.
            raise ValidationFailedError(
                f"Copies at {processor.value} cannot be deleted: it is not set up."
            )

        return adapter.erase(scope)

    def erasure_processors(self) -> list[SubProcessor]:
        return [
            adapter.processor
            for adapter in self._adapters.values()
            if adapter.deletes_copies
        ]

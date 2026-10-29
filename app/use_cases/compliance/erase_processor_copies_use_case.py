from typed_time_provider import Microseconds, WallClock

from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.processor_erasure import (
    ProcessorErasureJobPayload,
    ProcessorErasureScope,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditRecordCount,
    ErasedRecordCount,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount

# The audit entity of the copies at one processor: "langfuse_copies".
COPIES_ENTITY_SUFFIX: str = "_copies"


class EraseProcessorCopiesUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Queued job "erase_processor_copies": delete what one sub-processor
    keeps of a batch of a business's conversations or calls (after an
    erasure or the retention purge). A failure at the processor raises, so
    the queue retries it with backoff and finally shows it among the dead
    jobs of the admin's job list. Each finished deletion is audited in the
    business's log as DELETE of the processor's copies, with how many
    records it deleted (ids only, nothing personal).
    """

    def __init__(
        self,
        processor_erasure: ProcessorErasureFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._processor_erasure: ProcessorErasureFacilitatorContract = processor_erasure
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        business_id: BusinessId | None = input_data.business_id
        if business_id is None:
            raise ValidationFailedError("A processor erasure job names no business.")

        payload = ProcessorErasureJobPayload.model_validate_json(
            str(input_data.payload)
        )
        deleted: ErasedRecordCount = self._processor_erasure.erase(
            payload.processor,
            ProcessorErasureScope(
                business_id=business_id,
                reason=payload.reason,
                conversation_ids=payload.conversation_ids,
                provider_call_ids=payload.provider_call_ids,
            ),
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business_id,
                action=AuditAction.DELETE,
                entity=AuditEntityName(
                    f"{payload.processor.value}{COPIES_ENTITY_SUFFIX}"
                ),
                record_count=AuditRecordCount(int(deleted)),
                created_at=now,
                updated_at=now,
            )
        )
        return JobReport(processed_count=ProcessedItemCount(int(deleted)))

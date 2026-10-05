"""
Deleting the copies at the sub-processors: one queued job per processor
and batch of up to 100 references, the deletions themselves (Langfuse
traces by session, ElevenLabs conversations), the audited job, and the
documented no-op for Meta and Telegram.
"""

import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.privacy.messaging_platform_erasure_adapter import (
    MessagingPlatformErasureAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.privacy.processor_erasure_facilitator import (
    ProcessorErasureFacilitator,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.privacy import ProcessorErasureReason, SubProcessor
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.processor_erasure import (
    ProcessorErasureJobPayload,
    ProcessorErasureScope,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.compliance.erase_processor_copies_use_case import (
    EraseProcessorCopiesUseCase,
)
from app.utilities.privacy.processor_erasure_jobs import ERASE_PROCESSOR_COPIES_JOB
from tests.privacy.processor_erasure_doubles import (
    ProcessorErasureBed,
    RecordingJobQueue,
)

BUSINESS_ID: BusinessId = BusinessId()


def scope(conversations: int = 0, calls: int = 0) -> ProcessorErasureScope:
    return ProcessorErasureScope(
        business_id=BUSINESS_ID,
        reason=ProcessorErasureReason.CONTACT_ERASURE,
        conversation_ids=[ConversationId() for _ in range(conversations)],
        provider_call_ids=[ProviderCallId(f"conv_{index}") for index in range(calls)],
    )


def payloads(bed: ProcessorErasureBed) -> list[ProcessorErasureJobPayload]:
    return [
        ProcessorErasureJobPayload.model_validate_json(str(job.payload))
        for job in bed.job_queue.jobs
    ]


def test_each_processor_gets_its_own_jobs_of_at_most_a_hundred_references() -> None:
    bed = ProcessorErasureBed()

    queued = bed.facilitator().request_erasure(scope(conversations=250, calls=3))

    assert int(queued) == 4
    assert [
        (
            payload.processor,
            len(payload.conversation_ids),
            len(payload.provider_call_ids),
        )
        for payload in payloads(bed)
    ] == [
        (SubProcessor.LANGFUSE, 100, 0),
        (SubProcessor.LANGFUSE, 100, 0),
        (SubProcessor.LANGFUSE, 50, 0),
        (SubProcessor.ELEVENLABS, 0, 3),
    ]
    assert {job.name for job in bed.job_queue.jobs} == {ERASE_PROCESSOR_COPIES_JOB}
    assert {job.business_id for job in bed.job_queue.jobs} == {BUSINESS_ID}
    assert {job.lane for job in bed.job_queue.jobs} == {JobLane.DEFAULT}


def test_nothing_is_queued_for_nothing_and_meta_and_telegram_never_get_a_job() -> None:
    bed = ProcessorErasureBed()

    assert int(bed.facilitator().request_erasure(scope())) == 0
    assert bed.job_queue.jobs == []
    assert bed.facilitator().erasure_processors() == [
        SubProcessor.LANGFUSE,
        SubProcessor.ELEVENLABS,
    ]
    telegram = MessagingPlatformErasureAdapter(SubProcessor.TELEGRAM)
    assert telegram.copies_in(scope(conversations=1, calls=1)) is None
    assert int(telegram.erase(scope(conversations=1))) == 0
    assert telegram.deletes_copies is False


def test_langfuse_traces_go_by_session_in_batches_and_elevenlabs_by_call() -> None:
    bed = ProcessorErasureBed()
    target = scope(conversations=2, calls=2)
    first, second = target.conversation_ids
    bed.langfuse.sessions = {
        str(first): [f"trace-{index}" for index in range(230)],
        str(second): ["trace-x"],
        "someone-else": ["trace-other"],
    }
    facilitator = bed.facilitator()

    langfuse = facilitator.erase(SubProcessor.LANGFUSE, target)
    elevenlabs = facilitator.erase(SubProcessor.ELEVENLABS, target)

    assert int(langfuse) == 231
    assert "trace-other" not in bed.langfuse.deleted
    assert len(bed.langfuse.deleted) == 231
    assert int(elevenlabs) == 2
    assert bed.elevenlabs.deleted == ["conv_0", "conv_1"]


def test_a_processor_no_longer_set_up_refuses_instead_of_retrying() -> None:
    without_langfuse = ProcessorErasureFacilitator(
        adapters=[], job_queue=RecordingJobQueue()
    )

    with pytest.raises(ValidationFailedError, match="not set up"):
        without_langfuse.erase(SubProcessor.LANGFUSE, scope(conversations=1))


def build_job(
    bed: ProcessorErasureBed,
) -> tuple[EraseProcessorCopiesUseCase, AuditLogRepository]:
    audit = AuditLogRepository(InMemoryDocumentCollectionAdapter(AuditLogEntryDocument))
    clock = WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: 1_790_000_000_000_000_000,
    )
    return (
        EraseProcessorCopiesUseCase(
            processor_erasure=bed.facilitator(),
            audit_log_repo=audit,
            wall_clock=clock,
        ),
        audit,
    )


def job_input(
    bed: ProcessorErasureBed, business_id: BusinessId | None
) -> QueuedJobInput:
    return QueuedJobInput(
        job_id=QueuedJobId(),
        job_name=ERASE_PROCESSOR_COPIES_JOB,
        payload=JobPayloadJson(str(bed.job_queue.jobs[0].payload)),
        business_id=business_id,
    )


def test_the_job_deletes_and_audits_how_many_and_a_failure_is_retried() -> None:
    bed = ProcessorErasureBed()
    target = scope(conversations=1)
    bed.langfuse.sessions = {str(target.conversation_ids[0]): ["t1", "t2", "t3"]}
    bed.facilitator().request_erasure(target)
    job, audit = build_job(bed)
    bed.langfuse.failures_left = 1

    with pytest.raises(ExternalServiceError):
        job.run(job_input(bed, BUSINESS_ID))
    assert audit.list_by_business(BUSINESS_ID) == []

    report = job.run(job_input(bed, BUSINESS_ID))

    assert int(report.processed_count) == 3
    [entry] = audit.list_by_business(BUSINESS_ID)
    assert (entry.action, str(entry.entity), entry.record_count) == (
        AuditAction.DELETE,
        "langfuse_copies",
        3,
    )
    assert entry.actor_id is None and entry.entity_id is None


def test_a_job_without_a_business_is_refused() -> None:
    bed = ProcessorErasureBed()
    bed.facilitator().request_erasure(scope(calls=1))
    job, _ = build_job(bed)

    with pytest.raises(ValidationFailedError, match="no business"):
        job.run(job_input(bed, None))

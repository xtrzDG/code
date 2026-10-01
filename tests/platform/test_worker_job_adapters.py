"""Job wrappers of the worker: retention purge and the trace flush."""

from typed_time_provider import Microseconds

from app.orchestrators.compliance.purge_expired_recordings_job_orchestrator import (
    PurgeExpiredRecordingsJobOrchestrator,
)
from app.schemas.dto.compliance import (
    PurgeExpiredRecordingsCommand,
    RecordingPurgeResult,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.observability import LlmGenerationTrace
from app.schemas.typings.compliance.constrained_integers import (
    DeletedRecordingCount,
    PurgedCallCount,
    ScannedBusinessCount,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.observability.flush_llm_traces_use_case import (
    FlushLlmTracesUseCase,
)

TICK: JobTick = JobTick(
    job_name=JobName("purge_expired_recordings"),
    scheduled_at=Microseconds(1_790_000_000_000_000),
)


class RecordingPurge:
    def __init__(self) -> None:
        self.commands: list[PurgeExpiredRecordingsCommand] = []

    def run(self, input_data: PurgeExpiredRecordingsCommand) -> RecordingPurgeResult:
        self.commands.append(input_data)
        return RecordingPurgeResult(
            scanned_businesses=ScannedBusinessCount(4),
            purged_calls=PurgedCallCount(3),
            deleted_recordings=DeletedRecordingCount(2),
        )


class CountingTraceFacilitator:
    def __init__(self) -> None:
        self.flushes: int = 0

    def record_generation(self, trace: LlmGenerationTrace) -> None:
        del trace

    def flush(self) -> None:
        self.flushes += 1


def test_retention_job_purges_every_business_and_reports_purged_calls() -> None:
    purge = RecordingPurge()

    report = PurgeExpiredRecordingsJobOrchestrator(purge).execute(TICK)

    assert purge.commands == [PurgeExpiredRecordingsCommand(business_id=None)]
    assert report.processed_count == 3


def test_trace_flush_job_flushes_the_journal() -> None:
    facilitator = CountingTraceFacilitator()

    report = FlushLlmTracesUseCase(facilitator).run(TICK)

    assert facilitator.flushes == 1
    assert report.processed_count == 0

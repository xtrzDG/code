from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.compliance import (
    PurgeExpiredRecordingsCommand,
    RecordingPurgeResult,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount


class PurgeExpiredRecordingsJobOrchestrator(OrchestratorContract[JobTick, JobReport]):
    """
    The daily retention job of the background worker: purge expired call
    recordings of every business (concept section 10, 90 days by default)
    and report how many calls were purged.
    """

    def __init__(
        self,
        purge_expired_recordings: UseCaseContract[
            PurgeExpiredRecordingsCommand,
            RecordingPurgeResult,
        ],
    ) -> None:
        self._purge_expired_recordings: UseCaseContract[
            PurgeExpiredRecordingsCommand,
            RecordingPurgeResult,
        ] = purge_expired_recordings

    def execute(self, input_data: JobTick) -> JobReport:
        del input_data
        result: RecordingPurgeResult = self._purge_expired_recordings.run(
            PurgeExpiredRecordingsCommand(business_id=None)
        )
        return JobReport(processed_count=ProcessedItemCount(int(result.purged_calls)))

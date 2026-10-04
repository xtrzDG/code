from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.compliance import (
    PurgeExpiredRecordingsCommand,
    RecordingPurgeResult,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.media import MessageMediaPurgeResult
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount


class PurgeExpiredRecordingsJobOrchestrator(OrchestratorContract[JobTick, JobReport]):
    """
    The daily retention job of the background worker: purge expired call
    recordings of every business (concept section 10, 90 days by default),
    then the voice notes and photos customers sent, kept as long, and report
    how many calls and files were purged.
    """

    def __init__(
        self,
        purge_expired_recordings: UseCaseContract[
            PurgeExpiredRecordingsCommand,
            RecordingPurgeResult,
        ],
        purge_expired_message_media: UseCaseContract[
            PurgeExpiredRecordingsCommand,
            MessageMediaPurgeResult,
        ],
    ) -> None:
        self._purge_expired_recordings: UseCaseContract[
            PurgeExpiredRecordingsCommand,
            RecordingPurgeResult,
        ] = purge_expired_recordings
        self._purge_expired_message_media: UseCaseContract[
            PurgeExpiredRecordingsCommand,
            MessageMediaPurgeResult,
        ] = purge_expired_message_media

    def execute(self, input_data: JobTick) -> JobReport:
        del input_data
        result: RecordingPurgeResult = self._purge_expired_recordings.run(
            PurgeExpiredRecordingsCommand(business_id=None)
        )
        media: MessageMediaPurgeResult = self._purge_expired_message_media.run(
            PurgeExpiredRecordingsCommand(business_id=None)
        )
        return JobReport(
            processed_count=ProcessedItemCount(
                int(result.purged_calls) + int(media.deleted_files)
            )
        )

import logging

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.repositories.analytics_repositories import (
    WebVitalSampleRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentCount

LOGGER: logging.Logger = logging.getLogger(__name__)
WEB_VITAL_RETENTION_SECONDS: int = 90 * 24 * 60 * 60
WEB_VITAL_ENTITY: AuditEntityName = AuditEntityName("web_vital_sample")


class PurgeWebVitalsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily retention job: delete the cabinet's Web Vital samples older than
    90 days (indexed, in small batches). A purge that removed samples is
    audited as RETENTION_PURGE without an actor or business (the samples
    name the person who reported them). Running it twice is harmless.
    """

    def __init__(
        self,
        web_vital_sample_repo: WebVitalSampleRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._web_vital_sample_repo: WebVitalSampleRepoContract = web_vital_sample_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        purged: DocumentCount = self._web_vital_sample_repo.delete_recorded_before(
            self._wall_clock.now_unix_with_delta(Seconds(-WEB_VITAL_RETENTION_SECONDS))
        )
        LOGGER.info("Purged %d Web Vital samples older than 90 days", int(purged))
        if int(purged) > 0:
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    action=AuditAction.RETENTION_PURGE,
                    entity=WEB_VITAL_ENTITY,
                    created_at=now,
                    updated_at=now,
                )
            )

        return JobReport(processed_count=ProcessedItemCount(int(purged)))

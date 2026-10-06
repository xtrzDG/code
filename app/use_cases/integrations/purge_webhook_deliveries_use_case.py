from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.integrations.webhook_records import WEBHOOK_DELIVERY_ENTITY


class PurgeWebhookDeliveriesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily, across businesses: delete the deliveries the log has kept for
    30 days (their bodies name customers). A purge that removed some is
    audited as RETENTION_PURGE with how many, without an actor or a
    business; running it twice is harmless.
    """

    def __init__(
        self,
        delivery_repo: WebhookDeliveryRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        purged = int(self._delivery_repo.delete_expired_before(now))
        if purged > 0:
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    action=AuditAction.RETENTION_PURGE,
                    entity=WEBHOOK_DELIVERY_ENTITY,
                    record_count=AuditRecordCount(purged),
                    created_at=now,
                    updated_at=now,
                )
            )

        return JobReport(processed_count=ProcessedItemCount(purged))

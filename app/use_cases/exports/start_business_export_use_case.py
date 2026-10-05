from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.privacy.business_exports import (
    BusinessExportView,
    StartBusinessExportCommand,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.exports.business_export_views import build_export_view
from app.use_cases.shared.business_export_queue import queue_business_export

BUSINESS_ENTITY: AuditEntityName = AuditEntityName("business")
ACTIVE_STATUSES: frozenset[BusinessExportStatus] = frozenset(
    {BusinessExportStatus.QUEUED, BusinessExportStatus.RUNNING}
)
RECENT: DocumentQueryLimit = DocumentQueryLimit(5)


class StartBusinessExportUseCase(
    UseCaseContract[StartBusinessExportCommand, BusinessExportView]
):
    """
    The owner asks for everything the business keeps: the worker writes a
    ZIP (a JSON file per collection and the CSV tables) into the encrypted
    export storage, and Settings → Privacy offers it for a day: up to three
    downloads, each through a one-time link of the owner who downloads.

    Owners only (never staff or read-only support), after a recent sign-in
    or step-up, audited (EXPORT of "business", the export's id). One export
    at a time: while one is queued or being written, it is returned.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        export_repo: BusinessExportRepoContract,
        job_queue: JobQueueFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._export_repo: BusinessExportRepoContract = export_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up

    def run(self, input_data: StartBusinessExportCommand) -> BusinessExportView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                access_mode=BusinessAccessMode.WRITE,
            )
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        active: BusinessExportDocument | None = next(
            (
                export
                for export in self._export_repo.list_latest(business.id, RECENT)
                if export.status in ACTIVE_STATUSES
            ),
            None,
        )
        if active is not None:
            return build_export_view(active, now)

        export: BusinessExportDocument = queue_business_export(
            self._export_repo,
            self._job_queue,
            business.id,
            input_data.user_id,
            input_data.request.language or business.owner_language,
            now,
        )
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.EXPORT,
                entity=BUSINESS_ENTITY,
                entity_id=AuditEntityReference(str(export.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return build_export_view(export, now)

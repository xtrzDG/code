from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
    ExportDownloadLinkRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_exports import (
    BusinessExportDocument,
    ExportDownloadLinkDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.privacy.business_exports import (
    ExportDownloadLinkCommand,
    ExportDownloadLinkView,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.privacy.constrained_integers import ExportDownloadLinkMinutes
from app.schemas.typings.privacy.constrained_strings import (
    BusinessExportToken,
    ExportDownloadTokenHash,
)
from app.use_cases.exports.business_export_views import (
    MAX_EXPORT_DOWNLOADS,
    download_path,
    is_downloadable,
)
from app.utilities.privacy.export_download_tokens import (
    download_link_id,
    generate_download_token,
    hash_download_token,
)

LINK_ENTITY: AuditEntityName = AuditEntityName("export_download_link")
MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000


class CreateExportDownloadLinkUseCase(
    UseCaseContract[ExportDownloadLinkCommand, ExportDownloadLinkView]
):
    """
    An owner asks for a one-time link to download a READY export: owners
    only, after a recent sign-in or step-up (401 step_up_required), audited
    (CREATE of "export_download_link", the export's id).

    The link carries 256 random bits, of which only the SHA-256 is kept;
    it works once, for EXPORT_DOWNLOAD_LINK_MINUTES, and only with a
    session of this owner. An export that is not ready, whose archive was
    deleted, or of another business is 404; one downloaded three times is
    409 (ask for a new export).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        export_repo: BusinessExportRepoContract,
        link_repo: ExportDownloadLinkRepoContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
        link_minutes: ExportDownloadLinkMinutes,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._export_repo: BusinessExportRepoContract = export_repo
        self._link_repo: ExportDownloadLinkRepoContract = link_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._link_minutes: ExportDownloadLinkMinutes = link_minutes

    def run(self, input_data: ExportDownloadLinkCommand) -> ExportDownloadLinkView:
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
        export: BusinessExportDocument | None = self._export_repo.get(
            business.id, input_data.export_id
        )
        if export is not None and int(export.download_count) >= int(
            MAX_EXPORT_DOWNLOADS
        ):
            raise ConflictError(
                "This export was downloaded three times already. Ask for a new export."
            )
        if export is None or not is_downloadable(export, now):
            raise NotFoundError("This export is not ready or no longer kept.")

        token: BusinessExportToken = generate_download_token()
        token_hash: ExportDownloadTokenHash = hash_download_token(token)
        expires_at = Microseconds(
            int(now) + int(self._link_minutes) * MICROSECONDS_PER_MINUTE
        )
        self._link_repo.save(
            ExportDownloadLinkDocument(
                id=download_link_id(token_hash),
                business_id=business.id,
                export_id=export.id,
                user_id=input_data.user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )
        )
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.CREATE,
                entity=LINK_ENTITY,
                entity_id=AuditEntityReference(str(export.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return ExportDownloadLinkView(
            download_path=download_path(business.id, export.id, token),
            expires_at=expires_at,
        )

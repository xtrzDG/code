from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.legal_registries import LegalDocumentRegistryContract
from app.contracts.repositories.compliance_repositories import (
    AuditLogRepoContract,
    DpaAcceptanceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.compliance import (
    AcceptDpaCommand,
    DpaAcceptanceView,
    DpaStatusView,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.analytics.product_event_drafts import dpa_accepted_event
from app.utilities.compliance.legal_endpoints import build_dpa_document_url
from app.utilities.localization.cldr_language_names import ENGLISH_LOCALE_IDENTIFIER


class AcceptDpaUseCase(UseCaseContract[AcceptDpaCommand, DpaStatusView]):
    """
    Owner accepts the data processing agreement version now in force.

    Each acceptance is kept (version, who, when) and audited; accepting the
    same version again records another acceptance rather than failing. A
    version whose text is not in the repository cannot be accepted: the
    owner must be able to read what they accept.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        dpa_acceptance_repo: DpaAcceptanceRepoContract,
        audit_log_repo: AuditLogRepoContract,
        legal_document_registry: LegalDocumentRegistryContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._dpa_acceptance_repo: DpaAcceptanceRepoContract = dpa_acceptance_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._legal_document_registry: LegalDocumentRegistryContract = (
            legal_document_registry
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events

    def run(self, input_data: AcceptDpaCommand) -> DpaStatusView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        version: DpaDocumentVersion = self._app_settings.dpa_document_version
        if (
            self._legal_document_registry.find_dpa(
                version,
                LanguageTag(ENGLISH_LOCALE_IDENTIFIER),
            )
            is None
        ):
            raise ConflictError(
                f"The data processing agreement {version} has no text to read, "
                "so it cannot be accepted yet."
            )

        now: Microseconds = self._wall_clock.now_unix()
        acceptance = DpaAcceptanceDocument(
            business_id=business.id,
            document_version=version,
            accepted_by=input_data.user_id,
            accepted_at=now,
            created_at=now,
            updated_at=now,
        )
        self._dpa_acceptance_repo.save(acceptance)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.CREATE,
                entity=AuditEntityName("dpa_acceptance"),
                entity_id=AuditEntityReference(str(acceptance.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        self._product_events.record(
            dpa_accepted_event(input_data.user_id, business.id, version)
        )
        return DpaStatusView(
            business_id=business.id,
            current_document_version=version,
            is_current_version_accepted=True,
            latest_acceptance=DpaAcceptanceView(
                id=acceptance.id,
                document_version=acceptance.document_version,
                accepted_by=acceptance.accepted_by,
                accepted_at=acceptance.accepted_at,
            ),
            document_url=build_dpa_document_url(version),
        )

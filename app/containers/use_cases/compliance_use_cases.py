from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.businesses import (
    BusinessQuery,
)
from app.schemas.dto.compliance import (
    AcceptDpaCommand,
    AuditLogPage,
    AuditLogQuery,
    ContactDataCommand,
    ContactDataExport,
    ContactErasureResult,
    ContactRecords,
    ContactRecordsQuery,
    DpaDocumentQuery,
    DpaDocumentView,
    DpaStatusView,
    PurgeExpiredRecordingsCommand,
    RecordingPurgeResult,
)
from app.schemas.dto.contacts import (
    ContactDetailView,
    ContactListQuery,
    ContactPage,
    ContactQuery,
)
from app.use_cases.compliance.accept_dpa_use_case import AcceptDpaUseCase
from app.use_cases.compliance.collect_contact_records_use_case import (
    CollectContactRecordsUseCase,
)
from app.use_cases.compliance.delete_contact_data_use_case import (
    DeleteContactDataUseCase,
)
from app.use_cases.compliance.export_contact_data_use_case import (
    ExportContactDataUseCase,
)
from app.use_cases.compliance.get_dpa_document_use_case import (
    GetDpaDocumentUseCase,
)
from app.use_cases.compliance.get_dpa_status_use_case import GetDpaStatusUseCase
from app.use_cases.compliance.list_audit_log_use_case import ListAuditLogUseCase
from app.use_cases.compliance.purge_expired_recordings_use_case import (
    PurgeExpiredRecordingsUseCase,
)
from app.use_cases.contacts.get_contact_use_case import GetContactUseCase
from app.use_cases.contacts.list_contacts_use_case import ListContactsUseCase


class ComplianceUseCasesContainer(containers.DeclarativeContainer):
    """
    Compliance: the DPA, the audit log, contacts and their data rights (export,
    erasure), retention of call recordings.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    accept_dpa_use_case: Factory[UseCaseContract[AcceptDpaCommand, DpaStatusView]] = (
        Factory(
            AcceptDpaUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            dpa_acceptance_repo=repositories.dpa_acceptance_repo,
            audit_log_repo=repositories.audit_log_repo,
            legal_document_registry=registries.legal_document_registry,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    get_dpa_status_use_case: Factory[UseCaseContract[BusinessQuery, DpaStatusView]] = (
        Factory(
            GetDpaStatusUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            dpa_acceptance_repo=repositories.dpa_acceptance_repo,
            legal_document_registry=registries.legal_document_registry,
            app_settings=config.app_settings,
        )
    )
    get_dpa_document_use_case: Factory[
        UseCaseContract[DpaDocumentQuery, DpaDocumentView]
    ] = Factory(
        GetDpaDocumentUseCase,
        legal_document_registry=registries.legal_document_registry,
    )
    list_audit_log_use_case: Factory[UseCaseContract[AuditLogQuery, AuditLogPage]] = (
        Factory(
            ListAuditLogUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            audit_log_repo=repositories.audit_log_repo,
        )
    )
    list_contacts_use_case: Factory[UseCaseContract[ContactListQuery, ContactPage]] = (
        Factory(
            ListContactsUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            contact_repo=repositories.contact_repo,
            conversation_repo=repositories.conversation_repo,
            booking_repo=repositories.booking_repo,
            lead_repo=repositories.lead_repo,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
            phone_number_parser=utilities.phone_number_parser,
        )
    )
    get_contact_use_case: Factory[UseCaseContract[ContactQuery, ContactDetailView]] = (
        Factory(
            GetContactUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            contact_repo=repositories.contact_repo,
            conversation_repo=repositories.conversation_repo,
            booking_repo=repositories.booking_repo,
            lead_repo=repositories.lead_repo,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    collect_contact_records_use_case: Factory[
        UseCaseContract[ContactRecordsQuery, ContactRecords]
    ] = Factory(
        CollectContactRecordsUseCase,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        call_repo=repositories.call_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
    )
    export_contact_data_use_case: Factory[
        UseCaseContract[ContactDataCommand, ContactDataExport]
    ] = Factory(
        ExportContactDataUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        collect_contact_records=collect_contact_records_use_case,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    delete_contact_data_use_case: Factory[
        UseCaseContract[ContactDataCommand, ContactErasureResult]
    ] = Factory(
        DeleteContactDataUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        collect_contact_records=collect_contact_records_use_case,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        llm_turn_repo=repositories.llm_turn_repo,
        call_repo=repositories.call_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        recording_storage=adapters.recording_storage,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    purge_expired_recordings_use_case: Factory[
        UseCaseContract[PurgeExpiredRecordingsCommand, RecordingPurgeResult]
    ] = Factory(
        PurgeExpiredRecordingsUseCase,
        business_repo=repositories.business_repo,
        call_repo=repositories.call_repo,
        recording_storage=adapters.recording_storage,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

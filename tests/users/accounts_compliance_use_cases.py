"""The accounts testbed's compliance and contact use cases, wired."""

from collections.abc import Mapping

from typed_time_provider import Microseconds, WallClock

from app.registries.legal.legal_document_registry import LegalDocumentRegistry
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
from app.use_cases.compliance.get_dpa_document_use_case import GetDpaDocumentUseCase
from app.use_cases.compliance.get_dpa_status_use_case import GetDpaStatusUseCase
from app.use_cases.compliance.list_audit_log_use_case import ListAuditLogUseCase
from app.use_cases.compliance.purge_expired_recordings_use_case import (
    PurgeExpiredRecordingsUseCase,
)
from app.use_cases.contacts.get_contact_use_case import GetContactUseCase
from app.use_cases.contacts.list_contacts_use_case import ListContactsUseCase
from tests.users.accounts_user_use_cases import AccountsUserUseCases


class AccountsComplianceUseCases(AccountsUserUseCases):
    """DPA, audit log, contacts, data rights and recording retention use cases."""

    def __init__(self, environment_variables: Mapping[str, str]) -> None:
        super().__init__(environment_variables)
        wall_clock: WallClock[Microseconds] = self.clock.build_wall_clock()

        collect_contact_records = CollectContactRecordsUseCase(
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            call_repo=self.call_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
            note_repo=self.conversation_note_repo,
        )
        self.legal_document_registry = LegalDocumentRegistry()
        self.accept_dpa = AcceptDpaUseCase(
            authorize_business_access=self.authorize_business_access,
            dpa_acceptance_repo=self.dpa_acceptance_repo,
            audit_log_repo=self.audit_log_repo,
            legal_document_registry=self.legal_document_registry,
            app_settings=self.settings,
            wall_clock=wall_clock,
            product_events=self.product_events,
        )
        self.get_dpa_status = GetDpaStatusUseCase(
            authorize_business_access=self.authorize_business_access,
            dpa_acceptance_repo=self.dpa_acceptance_repo,
            legal_document_registry=self.legal_document_registry,
            app_settings=self.settings,
        )
        self.list_audit_log = ListAuditLogUseCase(
            authorize_business_access=self.authorize_business_access,
            audit_log_repo=self.audit_log_repo,
        )
        self.get_dpa_document = GetDpaDocumentUseCase(
            legal_document_registry=self.legal_document_registry
        )
        self.list_contacts = ListContactsUseCase(
            authorize_business_access=self.authorize_business_access,
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
            phone_number_parser=self.phone_parser,
        )
        self.get_contact = GetContactUseCase(
            authorize_business_access=self.authorize_business_access,
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.export_contact_data = ExportContactDataUseCase(
            authorize_business_access=self.authorize_business_access,
            collect_contact_records=collect_contact_records,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.delete_contact_data = DeleteContactDataUseCase(
            authorize_business_access=self.authorize_business_access,
            collect_contact_records=collect_contact_records,
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            llm_turn_repo=self.llm_turn_repo,
            call_repo=self.call_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
            recording_storage=self.recording_storage,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
            note_repo=self.conversation_note_repo,
        )
        self.purge_expired_recordings = PurgeExpiredRecordingsUseCase(
            business_repo=self.business_repo,
            call_repo=self.call_repo,
            recording_storage=self.recording_storage,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )

"""The accounts testbed's compliance and contact use cases, wired."""

from collections.abc import Mapping

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.legal.legal_document_registry import LegalDocumentRegistry
from app.repositories.business_repositories import ChannelRepository
from app.repositories.call_follow_up_repositories import MissedCallRepository
from app.repositories.delivery_repositories import (
    InboundEventRepository,
    OutboundMessageRepository,
)
from app.repositories.feedback_repositories import FeedbackRequestRepository
from app.repositories.message_media_repository import MessageMediaRepository
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
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
from tests.media.media_fakes import InMemoryMediaStorage
from tests.privacy.processor_erasure_doubles import ProcessorErasureBed
from tests.privacy.suppression_doubles import build_suppression_list
from tests.users.accounts_user_use_cases import AccountsUserUseCases


class AccountsComplianceUseCases(AccountsUserUseCases):
    """DPA, audit log, contacts, data rights and recording retention use cases."""

    def __init__(
        self,
        environment_variables: Mapping[str, str],
        enforce_step_up: bool = False,
    ) -> None:
        super().__init__(environment_variables, enforce_step_up)
        wall_clock: WallClock[Microseconds] = self.clock.build_wall_clock()
        # A visitor's traces outside their conversations, and the STOP list.
        self.channel_repo = ChannelRepository(
            InMemoryDocumentCollectionAdapter(ChannelDocument)
        )
        self.missed_call_repo = MissedCallRepository(
            InMemoryDocumentCollectionAdapter(MissedCallDocument)
        )
        self.outbound_message_repo = OutboundMessageRepository(
            InMemoryDocumentCollectionAdapter(OutboundMessageDocument)
        )
        self.inbound_event_repo = InboundEventRepository(
            InMemoryDocumentCollectionAdapter(InboundEventDocument)
        )
        self.feedback_request_repo = FeedbackRequestRepository(
            InMemoryDocumentCollectionAdapter(FeedbackRequestDocument)
        )
        self.suppression_list = build_suppression_list()

        collect_contact_records = CollectContactRecordsUseCase(
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            call_repo=self.call_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
            note_repo=self.conversation_note_repo,
            channel_repo=self.channel_repo,
            missed_call_repo=self.missed_call_repo,
            outbound_message_repo=self.outbound_message_repo,
            inbound_event_repo=self.inbound_event_repo,
            feedback_request_repo=self.feedback_request_repo,
        )
        self.legal_document_registry = LegalDocumentRegistry()
        self.accept_dpa = AcceptDpaUseCase(
            authorize_business_access=self.authorize_business_access,
            dpa_acceptance_repo=self.dpa_acceptance_repo,
            business_repo=self.business_repo,
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
            contact_activity_repo=self.contact_activity_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
            phone_number_parser=self.phone_parser,
        )
        self.get_contact = GetContactUseCase(
            authorize_business_access=self.authorize_business_access,
            contact_repo=self.contact_repo,
            contact_activity_repo=self.contact_activity_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.export_contact_data = ExportContactDataUseCase(
            authorize_business_access=self.authorize_business_access,
            collect_contact_records=collect_contact_records,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
            step_up=self.step_up,
            suppression_list=self.suppression_list,
        )
        # The voice notes and photos customers sent (erased with the data).
        self.media_storage = InMemoryMediaStorage()
        self.message_media_repo = MessageMediaRepository(
            InMemoryDocumentCollectionAdapter(MessageMediaDocument)
        )
        # Langfuse and ElevenLabs, whose copies the erasure deletes by jobs.
        self.processor_erasure = ProcessorErasureBed()
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
            step_up=self.step_up,
            note_repo=self.conversation_note_repo,
            media_storage=self.media_storage,
            message_media_repo=self.message_media_repo,
            suppression_list=self.suppression_list,
            missed_call_repo=self.missed_call_repo,
            outbound_message_repo=self.outbound_message_repo,
            inbound_event_repo=self.inbound_event_repo,
            feedback_request_repo=self.feedback_request_repo,
            processor_erasure=self.processor_erasure.facilitator(),
        )
        self.purge_expired_recordings = PurgeExpiredRecordingsUseCase(
            business_repo=self.business_repo,
            call_repo=self.call_repo,
            recording_storage=self.recording_storage,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )

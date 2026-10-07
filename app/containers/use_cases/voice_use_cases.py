from dependency_injector import containers
from dependency_injector.providers import Callable, DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.factories import is_recording_archive_enabled
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.conversation_use_cases import (
    ConversationUseCasesContainer,
)
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.spend_guard_use_cases import SpendGuardUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.call_audits import CallAudit, CallAuditRequest
from app.schemas.dto.conversations import VoiceToolCallRequest
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.voice_webhooks import (
    CallInitiationData,
    CallInitiationWebhookRequest,
    FinishedCallReport,
    PostCallWebhookRequest,
    RecordedCall,
    VoiceToolWebhookRequest,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.voice.audit_call_replies_use_case import (
    AuditCallRepliesUseCase,
)
from app.use_cases.voice.authenticate_post_call_use_case import (
    AuthenticatePostCallUseCase,
)
from app.use_cases.voice.authenticate_voice_tool_call_use_case import (
    AuthenticateVoiceToolCallUseCase,
)
from app.use_cases.voice.call_message_outbox import CallMessageOutbox
from app.use_cases.voice.finished_call.record_finished_call_use_case import (
    RecordFinishedCallUseCase,
)
from app.use_cases.voice.recordings.archive_call_recording_use_case import (
    ArchiveCallRecordingUseCase,
)
from app.use_cases.voice.recordings.schedule_recording_archive_use_case import (
    ScheduleRecordingArchiveUseCase,
)
from app.use_cases.voice.remove_voice_agent_use_case import RemoveVoiceAgentUseCase
from app.use_cases.voice.send_call_confirmation_use_case import (
    SendCallConfirmationUseCase,
)
from app.use_cases.voice.send_call_links_use_case import SendCallLinksUseCase
from app.use_cases.voice.start_voice_call_use_case import StartVoiceCallUseCase


class VoiceUseCasesContainer(containers.DeclarativeContainer):
    """
    Voice calls (ElevenLabs Agents): webhooks, finished calls and the check
    of what the assistant said, confirmations, and switching the voice agent
    off when voice leaves the live service.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_use_cases: ConversationUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    follow_up_use_cases: FollowUpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    spend_guard_use_cases: SpendGuardUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Switches the voice agent off when voice leaves the live service.
    remove_voice_agent_use_case: Factory[UseCaseContract[BusinessId, None]] = Factory(
        RemoveVoiceAgentUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
        voice_agent_provisioner=adapters.voice_agent_provisioner,
    )

    # --- Voice webhooks (ElevenLabs Agents).
    authenticate_voice_tool_call_use_case: Factory[
        UseCaseContract[VoiceToolWebhookRequest, VoiceToolCallRequest]
    ] = Factory(
        AuthenticateVoiceToolCallUseCase,
        business_repo=repositories.business_repo,
        voice_webhook_adapter=adapters.voice_webhook_adapter,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
    )
    start_voice_call_use_case: Factory[
        UseCaseContract[CallInitiationWebhookRequest, CallInitiationData]
    ] = Factory(
        StartVoiceCallUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        channel_repo=repositories.channel_repo,
        plan_registry=registries.plan_registry,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        contact_repo=repositories.contact_repo,
        booking_repo=repositories.booking_repo,
        resource_repo=repositories.resource_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        voice_webhook_adapter=adapters.voice_webhook_adapter,
        phone_number_parser=utilities.phone_number_parser,
        build_call_greeting=conversation_use_cases.build_call_greeting_use_case,
        app_settings=config.app_settings,
        check_spend=spend_guard_use_cases.check_business_spend_use_case,
    )
    audit_call_replies_use_case: Factory[
        UseCaseContract[CallAuditRequest, CallAudit]
    ] = Factory(
        AuditCallRepliesUseCase,
        business_repo=repositories.business_repo,
        call_repo=repositories.call_repo,
        conversation_repo=repositories.conversation_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        message_repo=repositories.message_repo,
        booking_repo=repositories.booking_repo,
        handoff_to_human=follow_up_use_cases.handoff_to_human_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    authenticate_post_call_use_case: Factory[
        UseCaseContract[PostCallWebhookRequest, FinishedCallReport | None]
    ] = Factory(
        AuthenticatePostCallUseCase,
        voice_webhook_adapter=adapters.voice_webhook_adapter,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_finished_call_use_case: Factory[
        UseCaseContract[FinishedCallReport, RecordedCall]
    ] = Factory(
        RecordFinishedCallUseCase,
        channel_repo=repositories.channel_repo,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        conversation_repo=repositories.conversation_repo,
        call_repo=repositories.call_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        usage_event_repo=repositories.usage_event_repo,
        audit_log_repo=repositories.audit_log_repo,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Messages to a caller after the call go through the outbox.
    call_message_outbox: Factory[CallMessageOutbox] = Factory(
        CallMessageOutbox,
        channel_repo=repositories.channel_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=facilitators.job_queue_facilitator,
        unit_of_work=adapters.storage_unit_of_work,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_call_links_use_case: Factory[UseCaseContract[RecordedCall, bool]] = Factory(
        SendCallLinksUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        call_messages=call_message_outbox,
        text_resolver=utilities.localized_text_resolver,
    )
    send_call_confirmation_use_case: Factory[UseCaseContract[RecordedCall, bool]] = (
        Factory(
            SendCallConfirmationUseCase,
            business_repo=repositories.business_repo,
            booking_repo=repositories.booking_repo,
            contact_repo=repositories.contact_repo,
            call_messages=call_message_outbox,
            text_resolver=utilities.localized_text_resolver,
        )
    )
    # Recordings archived from the voice platform into the EU object storage
    # (RECORDINGS_STORAGE=s3): queued after a call, run by the worker.
    schedule_recording_archive_use_case: Factory[
        UseCaseContract[RecordedCall, bool]
    ] = Factory(
        ScheduleRecordingArchiveUseCase,
        call_repo=repositories.call_repo,
        job_queue=facilitators.job_queue_facilitator,
        is_archive_enabled=Callable(
            is_recording_archive_enabled, settings=config.app_settings
        ),
    )
    archive_call_recording_use_case: Factory[
        UseCaseContract[QueuedJobInput, JobReport]
    ] = Factory(
        ArchiveCallRecordingUseCase,
        call_repo=repositories.call_repo,
        recording_storage=adapters.recording_storage,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

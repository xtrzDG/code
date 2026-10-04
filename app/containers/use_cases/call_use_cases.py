from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calls.call_settings import (
    CallSettingsQuery,
    CallSettingsView,
    TextBackPage,
    TextBackPageQuery,
    UpdateCallSettingsCommand,
)
from app.schemas.dto.calls.call_summaries import CallSummaryOutcome, CallSummaryRequest
from app.schemas.dto.calls.missed_calls import (
    MissedCallReport,
    PbxCallWebhookRequest,
    RegisteredMissedCall,
    StoredFinishedCall,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.voice_webhooks import PostCallWebhookRequest, RecordedCall
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.use_cases.voice.call_settings.get_call_settings_use_case import (
    GetCallSettingsUseCase,
)
from app.use_cases.voice.call_settings.list_text_backs_use_case import (
    ListTextBacksUseCase,
)
from app.use_cases.voice.call_settings.update_call_settings_use_case import (
    UpdateCallSettingsUseCase,
)
from app.use_cases.voice.finished_call.open_call_conversation_use_case import (
    OpenCallConversationUseCase,
)
from app.use_cases.voice.missed_calls.find_missed_voice_call_use_case import (
    FindMissedVoiceCallUseCase,
)
from app.use_cases.voice.missed_calls.notify_missed_call_use_case import (
    NotifyMissedCallUseCase,
)
from app.use_cases.voice.missed_calls.read_failed_call_start_use_case import (
    ReadFailedCallStartUseCase,
)
from app.use_cases.voice.missed_calls.read_pbx_missed_call_use_case import (
    ReadPbxMissedCallUseCase,
)
from app.use_cases.voice.missed_calls.register_missed_call_use_case import (
    RegisterMissedCallUseCase,
)
from app.use_cases.voice.missed_calls.send_text_back_use_case import (
    SendTextBackUseCase,
)
from app.use_cases.voice.missed_calls.text_back_messages import TextBackSms
from app.use_cases.voice.missed_calls.text_back_whatsapp import TextBackWhatsApp
from app.use_cases.voice.summaries.summarize_call_use_case import (
    SummarizeCallUseCase,
)


class CallUseCasesContainer(containers.DeclarativeContainer):
    """
    What follows a phone call: the conversation of a call, the summary to
    staff, callers who did not get through (from the telephony line or the
    voice platform) and their text-backs, and Settings → Calls.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- After every call: its conversation and the summary to staff.
    open_call_conversation_use_case: Factory[
        UseCaseContract[StoredFinishedCall, RecordedCall]
    ] = Factory(
        OpenCallConversationUseCase,
        business_repo=repositories.business_repo,
        call_repo=repositories.call_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    summarize_call_use_case: Factory[
        UseCaseContract[CallSummaryRequest, CallSummaryOutcome]
    ] = Factory(
        SummarizeCallUseCase,
        business_repo=repositories.business_repo,
        call_repo=repositories.call_repo,
        contact_repo=repositories.contact_repo,
        booking_repo=repositories.booking_repo,
        call_settings_repo=repositories.call_settings_repo,
        llm_adapter=adapters.llm_adapter,
        staff_alerts=facilitators.staff_alert_facilitator,
        report_text_transformer=transformers.call_report_text_transformer,
        report_brief_transformer=transformers.call_report_brief_transformer,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Callers who did not get through and their text-backs.
    find_missed_voice_call_use_case: Factory[
        UseCaseContract[StoredFinishedCall, MissedCallReport | None]
    ] = Factory(FindMissedVoiceCallUseCase)
    read_pbx_missed_call_use_case: Factory[
        UseCaseContract[PbxCallWebhookRequest, MissedCallReport | None]
    ] = Factory(
        ReadPbxMissedCallUseCase,
        pbx_webhook_adapter=adapters.calls.pbx_webhook_adapter,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    read_failed_call_start_use_case: Factory[
        UseCaseContract[PostCallWebhookRequest, MissedCallReport | None]
    ] = Factory(
        ReadFailedCallStartUseCase,
        voice_webhook_adapter=adapters.voice_webhook_adapter,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    register_missed_call_use_case: Factory[
        UseCaseContract[MissedCallReport, RegisteredMissedCall | None]
    ] = Factory(
        RegisterMissedCallUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        missed_call_repo=repositories.missed_call_repo,
        call_settings_repo=repositories.call_settings_repo,
        country_registry=registries.country_registry,
        rate_limits=registries.request_rate_limit_registry,
        job_queue=facilitators.job_queue_facilitator,
        phone_number_parser=utilities.phone_number_parser,
        sms_client=clients.twilio_messaging_client,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    notify_missed_call_use_case: Factory[
        UseCaseContract[RegisteredMissedCall | None, DeliveredNotificationCount]
    ] = Factory(
        NotifyMissedCallUseCase,
        business_repo=repositories.business_repo,
        call_settings_repo=repositories.call_settings_repo,
        staff_alerts=facilitators.staff_alert_facilitator,
        report_text_transformer=transformers.call_report_text_transformer,
        report_brief_transformer=transformers.call_report_brief_transformer,
        phone_number_parser=utilities.phone_number_parser,
    )
    send_text_back_use_case: Factory[UseCaseContract[QueuedJobInput, JobReport]] = (
        Factory(
            SendTextBackUseCase,
            missed_call_repo=repositories.missed_call_repo,
            business_repo=repositories.business_repo,
            call_settings_repo=repositories.call_settings_repo,
            contact_repo=repositories.contact_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            whatsapp=Factory(
                TextBackWhatsApp,
                channel_repo=repositories.channel_repo,
                outbound_message_repo=repositories.outbound_message_repo,
                job_queue=facilitators.job_queue_facilitator,
                unit_of_work=adapters.storage_unit_of_work,
                text_resolver=utilities.localized_text_resolver,
            ),
            sms=Factory(
                TextBackSms,
                sms_client=clients.twilio_messaging_client,
                text_resolver=utilities.localized_text_resolver,
            ),
            live_events=facilitators.event_publisher,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )

    # --- Settings → Calls (owners).
    get_call_settings_use_case: Factory[
        UseCaseContract[CallSettingsQuery, CallSettingsView]
    ] = Factory(
        GetCallSettingsUseCase,
        authorize_business_access=(
            account_use_cases.authorize_business_access_use_case
        ),
        call_settings_repo=repositories.call_settings_repo,
        channel_repo=repositories.channel_repo,
        text_resolver=utilities.localized_text_resolver,
        sms_client=clients.twilio_messaging_client,
    )
    update_call_settings_use_case: Factory[
        UseCaseContract[UpdateCallSettingsCommand, CallSettingsView]
    ] = Factory(
        UpdateCallSettingsUseCase,
        authorize_business_access=(
            account_use_cases.authorize_business_access_use_case
        ),
        call_settings_repo=repositories.call_settings_repo,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        text_resolver=utilities.localized_text_resolver,
        sms_client=clients.twilio_messaging_client,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_text_backs_use_case: Factory[
        UseCaseContract[TextBackPageQuery, TextBackPage]
    ] = Factory(
        ListTextBacksUseCase,
        authorize_business_access=(
            account_use_cases.authorize_business_access_use_case
        ),
        missed_call_repo=repositories.missed_call_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

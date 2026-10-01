from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.adapters import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.admin import (
    AdminClientPage,
    AdminClientQuery,
    AdminClientsQuery,
    AdminClientSummary,
    ClientCabinetAccess,
    ClientHealthView,
    ClientSummarySource,
    OpenClientCabinetCommand,
)
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.assistants import (
    AssembleAssistantVersionCommand,
    AssistantVersionActivation,
    AssistantVersionDetails,
    AssistantVersionQuery,
    AssistantVersionsQuery,
    AssistantVersionSummary,
    AutotestPlanningRequest,
    AutotestRunCompletion,
    AutotestRunFailure,
    AutotestRunPlan,
    AutotestRunProgress,
    AutotestRunView,
    AutotestScenarioPlanning,
    PublishAssistantVersionCommand,
    RollbackAssistantVersionCommand,
    RunAutotestsCommand,
)
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewQuery,
    BillingOverviewSource,
    CancelSubscriptionCommand,
    ChangePlanCommand,
    CheckoutSessionView,
    StartCheckoutCommand,
    StartTrialCommand,
    SubscribeCommand,
    SubscriptionOpening,
)
from app.schemas.dto.billing_ledger import (
    ClientCostQuery,
    ClientCostReport,
    DueInvoicesRequest,
)
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    BookingView,
    CancelBookingCommand,
    CreateBookingCommand,
    CreateLeadCommand,
    LeadView,
    RescheduleBookingCommand,
)
from app.schemas.dto.businesses import (
    BusinessQuery,
    BusinessView,
    ChangeMemberRoleCommand,
    CreateBusinessCommand,
    InviteStaffCommand,
    RemoveMemberCommand,
    UpdateBusinessSettingsCommand,
)
from app.schemas.dto.calendar import (
    CalendarConnectionOutcome,
    CalendarConnectionStatusQuery,
    CalendarConnectionStatusView,
)
from app.schemas.dto.call_recordings import CallRecordingQuery, RecordingAudio
from app.schemas.dto.catalog import (
    CallForwardingInstructions,
    CallForwardingInstructionsQuery,
    CountryList,
    CountryListRequest,
    CountryProfileRequest,
    CountryProfileView,
    LanguageList,
    LanguageListRequest,
    ParsePhoneNumberRequest,
    PlanQuoteList,
    PlanQuoteRequest,
)
from app.schemas.dto.channels import (
    ChannelInboundDelivery,
    ChannelListQuery,
    ChannelReplyDelivery,
    ChannelView,
    ConnectChannelCommand,
    CreateTelegramLinkCommand,
    DisableChannelCommand,
    MetaWebhookRequest,
    MetaWebhookVerificationRequest,
    PlatformBotWebhookOutcome,
    PlatformBotWebhookRequest,
    PlatformBotWebhookSetup,
    TelegramBotProfile,
    TelegramLinkView,
    TelegramWebhookRequest,
    WidgetConfigView,
    WidgetMessageCommand,
    WidgetMessagesQuery,
    WidgetMessagesView,
    WidgetReplyInput,
    WidgetReplyView,
    WidgetSnippetQuery,
    WidgetSnippetView,
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
from app.schemas.dto.conversation_engine import (
    GeneratedReply,
    PreparedTurn,
    ReplyRecord,
    VoiceToolCallRecord,
)
from app.schemas.dto.conversation_feed import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationPage,
    ConversationQuery,
    ConversationSummaryView,
    OwnerTestChatVersionQuery,
    RateConversationCommand,
    SendStaffMessageCommand,
    StaffMessageResult,
)
from app.schemas.dto.conversations import (
    AssistantReply,
    CallGreeting,
    CallGreetingRequest,
    InboundMessage,
    VoiceToolCallRequest,
    VoiceToolCallResult,
)
from app.schemas.dto.go_live import GoLiveReadiness, GoLiveReadinessRequest
from app.schemas.dto.handoffs import (
    HandoffCommand,
    HandoffResult,
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.schemas.dto.jobs import (
    JobReport,
    JobTick,
    QueuedJobInput,
)
from app.schemas.dto.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    PriceLookupQuery,
    PriceLookupResult,
    SendLinkQuery,
    SendLinkResult,
)
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    DeleteKnowledgeItemCommand,
    KnowledgeItemDeletion,
    KnowledgeItemDetails,
    KnowledgeItemList,
    KnowledgeItemListQuery,
    KnowledgeItemPage,
    KnowledgeItemQuery,
    UpdateKnowledgeItemCommand,
    UpsertKnowledgeItemsCommand,
)
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.dto.login_options import LoginOptionsQuery, LoginOptionsView
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
    DiscardedImportBatch,
    DiscardImportBatchCommand,
    ImportMenuCommand,
    MenuImportResult,
)
from app.schemas.dto.operations import (
    AnsweredQuestionResult,
    AnswerUnansweredQuestionCommand,
    BookingPage,
    CalendarConnectUrlView,
    CalendarDisconnectResult,
    CompleteCalendarConnectionCommand,
    DashboardStats,
    DashboardStatsQuery,
    DisconnectCalendarCommand,
    HandoffListItem,
    HandoffPage,
    LeadPage,
    ListBookingsQuery,
    ListHandoffsQuery,
    ListLeadsQuery,
    ListUnansweredQuestionsQuery,
    ManualBookingCommand,
    ResolveHandoffCommand,
    StartCalendarConnectionCommand,
    UnansweredQuestionPage,
    UpdateBookingCommand,
    UpdateLeadStatusCommand,
)
from app.schemas.dto.payments import (
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
)
from app.schemas.dto.profiles import (
    BusinessProfileQuery,
    BusinessProfileView,
    NicheCatalogQuery,
    NicheCatalogView,
    NicheDetailsView,
    NicheTemplateQuery,
    ProfileGapsQuery,
    ProfileGapsView,
    ProfileStepSaveResult,
    ProfileWizardQuery,
    ProfileWizardView,
    SaveProfileCommand,
    SaveProfileStepCommand,
)
from app.schemas.dto.resources import (
    CreateResourceCommand,
    CreateScheduleExceptionCommand,
    DeleteScheduleExceptionCommand,
    ResourceList,
    ResourceListQuery,
    ResourceView,
    ScheduleExceptionDeletion,
    ScheduleExceptionList,
    ScheduleExceptionListQuery,
    ScheduleExceptionView,
    UpdateResourceCommand,
)
from app.schemas.dto.staff_reply_templates import SetWhatsAppStaffTemplateCommand
from app.schemas.dto.users import (
    CurrentUserView,
    LoginSessionView,
    LogoutCommand,
    OtpChallengeView,
    StartOtpLoginCommand,
    UpdateCurrentUserCommand,
    UserView,
    VerifyOtpLoginCommand,
)
from app.schemas.dto.voice_webhooks import (
    CallInitiationData,
    CallInitiationWebhookRequest,
    FinishedCallReport,
    PostCallWebhookRequest,
    RecordedCall,
    VoiceToolWebhookRequest,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.strings import MetaWebhookChallenge
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.get_client_health_use_case import GetClientHealthUseCase
from app.use_cases.admin.list_clients_use_case import ListClientsUseCase
from app.use_cases.admin.open_client_cabinet_use_case import OpenClientCabinetUseCase
from app.use_cases.admin.summarize_client_use_case import SummarizeClientUseCase
from app.use_cases.assistants.activate_assistant_version_use_case import (
    ActivateAssistantVersionUseCase,
)
from app.use_cases.assistants.assemble_assistant_version_use_case import (
    AssembleAssistantVersionUseCase,
)
from app.use_cases.assistants.check_go_live_readiness_use_case import (
    CheckGoLiveReadinessUseCase,
)
from app.use_cases.assistants.get_assistant_version_use_case import (
    GetAssistantVersionUseCase,
)
from app.use_cases.assistants.get_go_live_readiness_use_case import (
    GetGoLiveReadinessUseCase,
)
from app.use_cases.assistants.list_assistant_versions_use_case import (
    ListAssistantVersionsUseCase,
)
from app.use_cases.assistants.publish_assistant_version_use_case import (
    PublishAssistantVersionUseCase,
)
from app.use_cases.assistants.resume_assistant_use_case import (
    ResumeAssistantUseCase,
)
from app.use_cases.assistants.rollback_assistant_version_use_case import (
    RollbackAssistantVersionUseCase,
)
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.autotests.abandon_autotest_run_use_case import (
    AbandonAutotestRunUseCase,
)
from app.use_cases.autotests.enqueue_autotest_run_use_case import (
    EnqueueAutotestRunUseCase,
)
from app.use_cases.autotests.finish_autotest_run_use_case import (
    FinishAutotestRunUseCase,
)
from app.use_cases.autotests.get_autotest_run_use_case import GetAutotestRunUseCase
from app.use_cases.autotests.plan_autotest_scenarios_use_case import (
    PlanAutotestScenariosUseCase,
)
from app.use_cases.autotests.record_autotest_progress_use_case import (
    RecordAutotestProgressUseCase,
)
from app.use_cases.autotests.resume_autotest_run_use_case import (
    ResumeAutotestRunUseCase,
)
from app.use_cases.autotests.start_autotest_run_use_case import StartAutotestRunUseCase
from app.use_cases.billing.assemble_billing_overview_use_case import (
    AssembleBillingOverviewUseCase,
)
from app.use_cases.billing.cancel_subscription_use_case import CancelSubscriptionUseCase
from app.use_cases.billing.change_plan_use_case import ChangePlanUseCase
from app.use_cases.billing.check_package_usage_use_case import CheckPackageUsageUseCase
from app.use_cases.billing.compute_client_cost_use_case import ComputeClientCostUseCase
from app.use_cases.billing.end_trials_use_case import EndTrialsUseCase
from app.use_cases.billing.enforce_grace_periods_use_case import (
    EnforceGracePeriodsUseCase,
)
from app.use_cases.billing.get_billing_overview_use_case import (
    GetBillingOverviewUseCase,
)
from app.use_cases.billing.invoice_usage_overage_use_case import (
    InvoiceUsageOverageUseCase,
)
from app.use_cases.billing.issue_due_invoices_use_case import IssueDueInvoicesUseCase
from app.use_cases.billing.open_subscription_use_case import (
    OpenSubscriptionUseCase,
)
from app.use_cases.billing.process_payment_webhook_use_case import (
    ProcessPaymentWebhookUseCase,
)
from app.use_cases.billing.start_checkout_use_case import StartCheckoutUseCase
from app.use_cases.billing.start_trial_use_case import StartTrialUseCase
from app.use_cases.bookings.cancel_booking_use_case import CancelBookingUseCase
from app.use_cases.bookings.check_availability_use_case import CheckAvailabilityUseCase
from app.use_cases.bookings.create_booking_use_case import CreateBookingUseCase
from app.use_cases.bookings.create_manual_booking_use_case import (
    CreateManualBookingUseCase,
)
from app.use_cases.bookings.list_bookings_use_case import ListBookingsUseCase
from app.use_cases.bookings.reschedule_booking_use_case import RescheduleBookingUseCase
from app.use_cases.bookings.send_booking_reminders_use_case import (
    SendBookingRemindersUseCase,
)
from app.use_cases.bookings.update_booking_use_case import UpdateBookingUseCase
from app.use_cases.businesses.change_member_role_use_case import (
    ChangeMemberRoleUseCase,
)
from app.use_cases.businesses.create_business_use_case import CreateBusinessUseCase
from app.use_cases.businesses.get_business_use_case import GetBusinessUseCase
from app.use_cases.businesses.invite_staff_use_case import InviteStaffUseCase
from app.use_cases.businesses.list_my_businesses_use_case import ListMyBusinessesUseCase
from app.use_cases.businesses.remove_member_use_case import RemoveMemberUseCase
from app.use_cases.businesses.update_business_settings_use_case import (
    UpdateBusinessSettingsUseCase,
)
from app.use_cases.calendar.complete_google_calendar_connection_use_case import (
    CompleteGoogleCalendarConnectionUseCase,
)
from app.use_cases.calendar.disconnect_google_calendar_use_case import (
    DisconnectGoogleCalendarUseCase,
)
from app.use_cases.calendar.get_google_calendar_connection_use_case import (
    GetGoogleCalendarConnectionUseCase,
)
from app.use_cases.calendar.start_google_calendar_connection_use_case import (
    StartGoogleCalendarConnectionUseCase,
)
from app.use_cases.catalog.get_country_profile_use_case import GetCountryProfileUseCase
from app.use_cases.catalog.list_countries_use_case import ListCountriesUseCase
from app.use_cases.catalog.list_languages_use_case import ListLanguagesUseCase
from app.use_cases.catalog.quote_plans_use_case import QuotePlansUseCase
from app.use_cases.channels.accept_widget_message_use_case import (
    AcceptWidgetMessageUseCase,
)
from app.use_cases.channels.build_widget_reply_use_case import BuildWidgetReplyUseCase
from app.use_cases.channels.configure_platform_bot_webhook_use_case import (
    ConfigurePlatformBotWebhookUseCase,
)
from app.use_cases.channels.connect_channel_use_case import ConnectChannelUseCase
from app.use_cases.channels.create_telegram_link_use_case import (
    CreateTelegramLinkUseCase,
)
from app.use_cases.channels.deliver_channel_reply_use_case import (
    DeliverChannelReplyUseCase,
)
from app.use_cases.channels.disable_channel_use_case import DisableChannelUseCase
from app.use_cases.channels.get_widget_config_use_case import GetWidgetConfigUseCase
from app.use_cases.channels.get_widget_messages_use_case import (
    GetWidgetMessagesUseCase,
)
from app.use_cases.channels.get_widget_snippet_use_case import GetWidgetSnippetUseCase
from app.use_cases.channels.handle_platform_bot_update_use_case import (
    HandlePlatformBotUpdateUseCase,
)
from app.use_cases.channels.list_channels_use_case import ListChannelsUseCase
from app.use_cases.channels.receive_meta_webhook_use_case import (
    ReceiveMetaWebhookUseCase,
)
from app.use_cases.channels.receive_telegram_webhook_use_case import (
    ReceiveTelegramWebhookUseCase,
)
from app.use_cases.channels.set_whatsapp_staff_template_use_case import (
    SetWhatsAppStaffTemplateUseCase,
)
from app.use_cases.channels.verify_meta_webhook_use_case import VerifyMetaWebhookUseCase
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
from app.use_cases.conversations.build_call_greeting_use_case import (
    BuildCallGreetingUseCase,
)
from app.use_cases.conversations.generate_assistant_reply_use_case import (
    GenerateAssistantReplyUseCase,
)
from app.use_cases.conversations.get_call_recording_use_case import (
    GetCallRecordingUseCase,
)
from app.use_cases.conversations.get_conversation_use_case import GetConversationUseCase
from app.use_cases.conversations.list_conversations_use_case import (
    ListConversationsUseCase,
)
from app.use_cases.conversations.open_voice_conversation_use_case import (
    OpenVoiceConversationUseCase,
)
from app.use_cases.conversations.prepare_conversation_turn_use_case import (
    PrepareConversationTurnUseCase,
)
from app.use_cases.conversations.rate_conversation_use_case import (
    RateConversationUseCase,
)
from app.use_cases.conversations.record_assistant_reply_use_case import (
    RecordAssistantReplyUseCase,
)
from app.use_cases.conversations.record_voice_tool_call_use_case import (
    RecordVoiceToolCallUseCase,
)
from app.use_cases.conversations.resolve_test_chat_version_use_case import (
    ResolveTestChatVersionUseCase,
)
from app.use_cases.conversations.run_assistant_tool_use_case import (
    RunAssistantToolUseCase,
)
from app.use_cases.conversations.send_staff_message_use_case import (
    SendStaffMessageUseCase,
)
from app.use_cases.example_use_case import ExampleUseCase
from app.use_cases.handoffs.answer_unanswered_question_use_case import (
    AnswerUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.handoff_to_human_use_case import HandoffToHumanUseCase
from app.use_cases.handoffs.list_handoffs_use_case import ListHandoffsUseCase
from app.use_cases.handoffs.list_unanswered_questions_use_case import (
    ListUnansweredQuestionsUseCase,
)
from app.use_cases.handoffs.record_unanswered_question_use_case import (
    RecordUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.resolve_handoff_use_case import ResolveHandoffUseCase
from app.use_cases.insights.get_dashboard_stats_use_case import GetDashboardStatsUseCase
from app.use_cases.knowledge.create_knowledge_item_use_case import (
    CreateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.delete_knowledge_item_use_case import (
    DeleteKnowledgeItemUseCase,
)
from app.use_cases.knowledge.get_knowledge_item_use_case import GetKnowledgeItemUseCase
from app.use_cases.knowledge.get_price_use_case import GetPriceUseCase
from app.use_cases.knowledge.list_knowledge_items_use_case import (
    ListKnowledgeItemsUseCase,
)
from app.use_cases.knowledge.search_knowledge_use_case import SearchKnowledgeUseCase
from app.use_cases.knowledge.send_link_use_case import SendLinkUseCase
from app.use_cases.knowledge.update_knowledge_item_use_case import (
    UpdateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.upsert_knowledge_items_use_case import (
    UpsertKnowledgeItemsUseCase,
)
from app.use_cases.leads.create_lead_use_case import CreateLeadUseCase
from app.use_cases.leads.list_leads_use_case import ListLeadsUseCase
from app.use_cases.leads.update_lead_status_use_case import UpdateLeadStatusUseCase
from app.use_cases.localization.build_call_forwarding_instructions_use_case import (
    BuildCallForwardingInstructionsUseCase,
)
from app.use_cases.localization.parse_phone_number_use_case import (
    ParsePhoneNumberUseCase,
)
from app.use_cases.menu_import.confirm_imported_items_use_case import (
    ConfirmImportedItemsUseCase,
)
from app.use_cases.menu_import.discard_import_batch_use_case import (
    DiscardImportBatchUseCase,
)
from app.use_cases.menu_import.import_menu_use_case import ImportMenuUseCase
from app.use_cases.observability.flush_llm_traces_use_case import FlushLlmTracesUseCase
from app.use_cases.profiles.compute_profile_gaps_use_case import (
    ComputeProfileGapsUseCase,
)
from app.use_cases.profiles.get_business_profile_use_case import (
    GetBusinessProfileUseCase,
)
from app.use_cases.profiles.get_niche_template_use_case import GetNicheTemplateUseCase
from app.use_cases.profiles.get_profile_wizard_use_case import GetProfileWizardUseCase
from app.use_cases.profiles.list_niche_templates_use_case import (
    ListNicheTemplatesUseCase,
)
from app.use_cases.profiles.save_profile_step_use_case import SaveProfileStepUseCase
from app.use_cases.profiles.save_profile_use_case import SaveProfileUseCase
from app.use_cases.resources.create_resource_use_case import CreateResourceUseCase
from app.use_cases.resources.create_schedule_exception_use_case import (
    CreateScheduleExceptionUseCase,
)
from app.use_cases.resources.delete_schedule_exception_use_case import (
    DeleteScheduleExceptionUseCase,
)
from app.use_cases.resources.list_resources_use_case import ListResourcesUseCase
from app.use_cases.resources.list_schedule_exceptions_use_case import (
    ListScheduleExceptionsUseCase,
)
from app.use_cases.resources.update_resource_use_case import UpdateResourceUseCase
from app.use_cases.users.authenticate_user_use_case import AuthenticateUserUseCase
from app.use_cases.users.get_current_user_use_case import GetCurrentUserUseCase
from app.use_cases.users.get_login_options_use_case import GetLoginOptionsUseCase
from app.use_cases.users.logout_use_case import LogoutUseCase
from app.use_cases.users.start_otp_login_use_case import StartOtpLoginUseCase
from app.use_cases.users.update_current_user_use_case import UpdateCurrentUserUseCase
from app.use_cases.users.verify_otp_login_use_case import VerifyOtpLoginUseCase
from app.use_cases.voice.authenticate_post_call_use_case import (
    AuthenticatePostCallUseCase,
)
from app.use_cases.voice.authenticate_voice_tool_call_use_case import (
    AuthenticateVoiceToolCallUseCase,
)
from app.use_cases.voice.record_finished_call_use_case import RecordFinishedCallUseCase
from app.use_cases.voice.remove_voice_agent_use_case import RemoveVoiceAgentUseCase
from app.use_cases.voice.send_call_confirmation_use_case import (
    SendCallConfirmationUseCase,
)
from app.use_cases.voice.start_voice_call_use_case import StartVoiceCallUseCase


class UseCasesContainer(containers.DeclarativeContainer):
    """
    Every use case, typed by its contract (input and output), so the
    orchestrator, pipeline and operator chains built on them are checked.

    Use cases are stateless: Factory, except the ones holding a cache.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Access to a business (owners, staff, audited platform admins).
    authorize_business_access_use_case: Factory[
        UseCaseContract[BusinessAccessRequest, BusinessDocument]
    ] = Factory(
        AuthorizeBusinessAccessUseCase,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Switches the voice agent off when voice leaves the live service.
    remove_voice_agent_use_case: Factory[UseCaseContract[BusinessId, None]] = Factory(
        RemoveVoiceAgentUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
        voice_agent_provisioner=adapters.voice_agent_provisioner,
    )

    # --- Catalog: countries, languages, plans, phone numbers.
    parse_phone_number_use_case: Factory[
        UseCaseContract[ParsePhoneNumberRequest, PhoneNumberDetails]
    ] = Factory(
        ParsePhoneNumberUseCase,
        phone_number_parser=utilities.phone_number_parser,
    )
    list_countries_use_case: Factory[
        UseCaseContract[CountryListRequest, CountryList]
    ] = Factory(
        ListCountriesUseCase,
        country_registry=registries.country_registry,
    )
    get_country_profile_use_case: Factory[
        UseCaseContract[CountryProfileRequest, CountryProfileView]
    ] = Factory(
        GetCountryProfileUseCase,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_languages_use_case: Factory[
        UseCaseContract[LanguageListRequest, LanguageList]
    ] = Factory(
        ListLanguagesUseCase,
        language_registry=registries.language_registry,
    )
    quote_plans_use_case: Factory[UseCaseContract[PlanQuoteRequest, PlanQuoteList]] = (
        Factory(
            QuotePlansUseCase,
            plan_registry=registries.plan_registry,
            country_registry=registries.country_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            localized_text_resolver=utilities.localized_text_resolver,
        )
    )
    build_call_forwarding_instructions_use_case: Factory[
        UseCaseContract[CallForwardingInstructionsQuery, CallForwardingInstructions]
    ] = Factory(
        BuildCallForwardingInstructionsUseCase,
        channel_repo=repositories.channel_repo,
        phone_number_parser=utilities.phone_number_parser,
        call_forwarding_guide_registry=registries.call_forwarding_guide_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )

    # --- Sign-in and the current user.
    start_otp_login_use_case: Factory[
        UseCaseContract[StartOtpLoginCommand, OtpChallengeView]
    ] = Factory(
        StartOtpLoginUseCase,
        otp_challenge_repo=repositories.otp_challenge_repo,
        phone_number_parser=utilities.phone_number_parser,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        otp_delivery_facilitator=facilitators.otp_delivery_facilitator,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        send_lock_registry=registries.login_code_send_lock_registry,
    )
    get_login_options_use_case: Factory[
        UseCaseContract[LoginOptionsQuery, LoginOptionsView]
    ] = Factory(
        GetLoginOptionsUseCase,
        country_registry=registries.country_registry,
        otp_delivery_facilitator=facilitators.otp_delivery_facilitator,
        app_settings=config.app_settings,
    )
    verify_otp_login_use_case: Factory[
        UseCaseContract[VerifyOtpLoginCommand, LoginSessionView]
    ] = Factory(
        VerifyOtpLoginUseCase,
        otp_challenge_repo=repositories.otp_challenge_repo,
        user_repo=repositories.user_repo,
        user_session_repo=repositories.user_session_repo,
        audit_log_repo=repositories.audit_log_repo,
        user_view_transformer=transformers.user_view_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    authenticate_user_use_case: Factory[UseCaseContract[AccessToken, UserId]] = Factory(
        AuthenticateUserUseCase,
        user_session_repo=repositories.user_session_repo,
        user_repo=repositories.user_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    logout_use_case: Factory[UseCaseContract[LogoutCommand, None]] = Factory(
        LogoutUseCase,
        user_session_repo=repositories.user_session_repo,
    )
    get_current_user_use_case: Factory[UseCaseContract[UserId, CurrentUserView]] = (
        Factory(
            GetCurrentUserUseCase,
            user_repo=repositories.user_repo,
            business_repo=repositories.business_repo,
            user_view_transformer=transformers.user_view_transformer,
        )
    )
    update_current_user_use_case: Factory[
        UseCaseContract[UpdateCurrentUserCommand, UserView]
    ] = Factory(
        UpdateCurrentUserUseCase,
        user_repo=repositories.user_repo,
        language_registry=registries.language_registry,
        user_view_transformer=transformers.user_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Businesses and teams.
    create_business_use_case: Factory[
        UseCaseContract[CreateBusinessCommand, BusinessView]
    ] = Factory(
        CreateBusinessUseCase,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        niche_template_registry=registries.niche_template_registry,
        business_view_transformer=transformers.business_view_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_my_businesses_use_case: Factory[
        UseCaseContract[UserId, list[BusinessView]]
    ] = Factory(
        ListMyBusinessesUseCase,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        business_view_transformer=transformers.business_view_transformer,
    )
    get_business_use_case: Factory[UseCaseContract[BusinessQuery, BusinessView]] = (
        Factory(
            GetBusinessUseCase,
            authorize_business_access=authorize_business_access_use_case,
            user_repo=repositories.user_repo,
            business_view_transformer=transformers.business_view_transformer,
        )
    )
    invite_staff_use_case: Factory[
        UseCaseContract[InviteStaffCommand, BusinessView]
    ] = Factory(
        InviteStaffUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        phone_number_parser=utilities.phone_number_parser,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    change_member_role_use_case: Factory[
        UseCaseContract[ChangeMemberRoleCommand, BusinessView]
    ] = Factory(
        ChangeMemberRoleUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    remove_member_use_case: Factory[
        UseCaseContract[RemoveMemberCommand, BusinessView]
    ] = Factory(
        RemoveMemberUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Compliance: DPA, audit log, data rights, retention.
    accept_dpa_use_case: Factory[UseCaseContract[AcceptDpaCommand, DpaStatusView]] = (
        Factory(
            AcceptDpaUseCase,
            authorize_business_access=authorize_business_access_use_case,
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
            authorize_business_access=authorize_business_access_use_case,
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
            authorize_business_access=authorize_business_access_use_case,
            audit_log_repo=repositories.audit_log_repo,
        )
    )
    list_contacts_use_case: Factory[UseCaseContract[ContactListQuery, ContactPage]] = (
        Factory(
            ListContactsUseCase,
            authorize_business_access=authorize_business_access_use_case,
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
            authorize_business_access=authorize_business_access_use_case,
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
        authorize_business_access=authorize_business_access_use_case,
        collect_contact_records=collect_contact_records_use_case,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    delete_contact_data_use_case: Factory[
        UseCaseContract[ContactDataCommand, ContactErasureResult]
    ] = Factory(
        DeleteContactDataUseCase,
        authorize_business_access=authorize_business_access_use_case,
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

    # --- Niche templates and the profile wizard.
    list_niche_templates_use_case: Factory[
        UseCaseContract[NicheCatalogQuery, NicheCatalogView]
    ] = Factory(
        ListNicheTemplatesUseCase,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    get_niche_template_use_case: Factory[
        UseCaseContract[NicheTemplateQuery, NicheDetailsView]
    ] = Factory(
        GetNicheTemplateUseCase,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    get_profile_wizard_use_case: Factory[
        UseCaseContract[ProfileWizardQuery, ProfileWizardView]
    ] = Factory(
        GetProfileWizardUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    get_business_profile_use_case: Factory[
        UseCaseContract[BusinessProfileQuery, BusinessProfileView]
    ] = Factory(
        GetBusinessProfileUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
    )
    save_profile_step_use_case: Factory[
        UseCaseContract[SaveProfileStepCommand, ProfileStepSaveResult]
    ] = Factory(
        SaveProfileStepUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        audit_log_repo=repositories.audit_log_repo,
        niche_template_registry=registries.niche_template_registry,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    save_profile_use_case: Factory[
        UseCaseContract[SaveProfileCommand, BusinessProfileView]
    ] = Factory(
        SaveProfileUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        audit_log_repo=repositories.audit_log_repo,
        niche_template_registry=registries.niche_template_registry,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    compute_profile_gaps_use_case: Factory[
        UseCaseContract[ProfileGapsQuery, ProfileGapsView]
    ] = Factory(
        ComputeProfileGapsUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )

    # --- Knowledge base (search_knowledge, get_price and send_link are tools).
    create_knowledge_item_use_case: Factory[
        UseCaseContract[CreateKnowledgeItemCommand, KnowledgeItemDetails]
    ] = Factory(
        CreateKnowledgeItemUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_knowledge_item_use_case: Factory[
        UseCaseContract[KnowledgeItemQuery, KnowledgeItemDetails]
    ] = Factory(
        GetKnowledgeItemUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    list_knowledge_items_use_case: Factory[
        UseCaseContract[KnowledgeItemListQuery, KnowledgeItemPage]
    ] = Factory(
        ListKnowledgeItemsUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    update_knowledge_item_use_case: Factory[
        UseCaseContract[UpdateKnowledgeItemCommand, KnowledgeItemDetails]
    ] = Factory(
        UpdateKnowledgeItemUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    delete_knowledge_item_use_case: Factory[
        UseCaseContract[DeleteKnowledgeItemCommand, KnowledgeItemDeletion]
    ] = Factory(
        DeleteKnowledgeItemUseCase,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    upsert_knowledge_items_use_case: Factory[
        UseCaseContract[UpsertKnowledgeItemsCommand, KnowledgeItemList]
    ] = Factory(
        UpsertKnowledgeItemsUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    search_knowledge_use_case: Factory[
        UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
    ] = Factory(
        SearchKnowledgeUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    get_price_use_case: Factory[
        UseCaseContract[PriceLookupQuery, PriceLookupResult]
    ] = Factory(
        GetPriceUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    send_link_use_case: Factory[UseCaseContract[SendLinkQuery, SendLinkResult]] = (
        Factory(
            SendLinkUseCase,
            business_profile_repo=repositories.business_profile_repo,
        )
    )

    # --- Resources, schedules and exceptions.
    create_resource_use_case: Factory[
        UseCaseContract[CreateResourceCommand, ResourceView]
    ] = Factory(
        CreateResourceUseCase,
        business_repo=repositories.business_repo,
        resource_repo=repositories.resource_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_resource_use_case: Factory[
        UseCaseContract[UpdateResourceCommand, ResourceView]
    ] = Factory(
        UpdateResourceUseCase,
        resource_repo=repositories.resource_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_resources_use_case: Factory[
        UseCaseContract[ResourceListQuery, ResourceList]
    ] = Factory(
        ListResourcesUseCase,
        resource_repo=repositories.resource_repo,
    )
    create_schedule_exception_use_case: Factory[
        UseCaseContract[CreateScheduleExceptionCommand, ScheduleExceptionView]
    ] = Factory(
        CreateScheduleExceptionUseCase,
        business_repo=repositories.business_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_schedule_exceptions_use_case: Factory[
        UseCaseContract[ScheduleExceptionListQuery, ScheduleExceptionList]
    ] = Factory(
        ListScheduleExceptionsUseCase,
        schedule_exception_repo=repositories.schedule_exception_repo,
    )
    delete_schedule_exception_use_case: Factory[
        UseCaseContract[DeleteScheduleExceptionCommand, ScheduleExceptionDeletion]
    ] = Factory(
        DeleteScheduleExceptionUseCase,
        schedule_exception_repo=repositories.schedule_exception_repo,
    )

    # --- Bookings (the booking tools share the business lock registry).
    check_availability_use_case: Factory[
        UseCaseContract[AvailabilityQuery, AvailabilityResult]
    ] = Factory(
        CheckAvailabilityUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    create_booking_use_case: Factory[
        UseCaseContract[CreateBookingCommand, BookingResult]
    ] = Factory(
        CreateBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.booking_confirmation_transformer,
        staff_notification_transformer=transformers.new_booking_notification_transformer,
        manager_broadcaster=facilitators.manager_broadcast_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    cancel_booking_use_case: Factory[
        UseCaseContract[CancelBookingCommand, BookingResult]
    ] = Factory(
        CancelBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.cancellation_confirmation_transformer,
        staff_notification_transformer=transformers.booking_cancelled_notification_transformer,
        manager_broadcaster=facilitators.manager_broadcast_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    reschedule_booking_use_case: Factory[
        UseCaseContract[RescheduleBookingCommand, BookingResult]
    ] = Factory(
        RescheduleBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.reschedule_confirmation_transformer,
        staff_notification_transformer=transformers.booking_moved_notification_transformer,
        manager_broadcaster=facilitators.manager_broadcast_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_bookings_use_case: Factory[UseCaseContract[ListBookingsQuery, BookingPage]] = (
        Factory(
            ListBookingsUseCase,
            business_repo=repositories.business_repo,
            booking_repo=repositories.booking_repo,
            resource_repo=repositories.resource_repo,
            contact_repo=repositories.contact_repo,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    create_manual_booking_use_case: Factory[
        UseCaseContract[ManualBookingCommand, BookingResult]
    ] = Factory(
        CreateManualBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.booking_confirmation_transformer,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_booking_use_case: Factory[
        UseCaseContract[UpdateBookingCommand, BookingView]
    ] = Factory(
        UpdateBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        resource_repo=repositories.resource_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_booking_reminders_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            SendBookingRemindersUseCase,
            business_repo=repositories.business_repo,
            business_profile_repo=repositories.business_profile_repo,
            booking_repo=repositories.booking_repo,
            resource_repo=repositories.resource_repo,
            contact_repo=repositories.contact_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            channel_message_sender=facilitators.channel_message_sender,
            reminder_transformer=transformers.booking_reminder_transformer,
            reminder_template_transformer=(
                transformers.booking_reminder_template_transformer
            ),
            wall_clock=time_provider.microsecond_wall_clock,
            whatsapp_reminder_template=(
                config.app_settings.provided.whatsapp_reminder_template_name
            ),
        )
    )

    # --- Leads, handoffs and unanswered questions.
    create_lead_use_case: Factory[UseCaseContract[CreateLeadCommand, LeadView]] = (
        Factory(
            CreateLeadUseCase,
            business_repo=repositories.business_repo,
            lead_repo=repositories.lead_repo,
            contact_repo=repositories.contact_repo,
            audit_log_repo=repositories.audit_log_repo,
            phone_number_parser=utilities.phone_number_parser,
            staff_notification_transformer=transformers.new_lead_notification_transformer,
            manager_broadcaster=facilitators.manager_broadcast_facilitator,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    list_leads_use_case: Factory[UseCaseContract[ListLeadsQuery, LeadPage]] = Factory(
        ListLeadsUseCase,
        business_repo=repositories.business_repo,
        lead_repo=repositories.lead_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_lead_status_use_case: Factory[
        UseCaseContract[UpdateLeadStatusCommand, LeadView]
    ] = Factory(
        UpdateLeadStatusUseCase,
        lead_repo=repositories.lead_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    handoff_to_human_use_case: Factory[
        UseCaseContract[HandoffCommand, HandoffResult]
    ] = Factory(
        HandoffToHumanUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        handoff_repo=repositories.handoff_repo,
        phone_number_parser=utilities.phone_number_parser,
        staff_notification_transformer=transformers.handoff_notification_transformer,
        customer_message_transformer=transformers.handoff_customer_message_transformer,
        manager_broadcaster=facilitators.manager_broadcast_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resolve_handoff_use_case: Factory[
        UseCaseContract[ResolveHandoffCommand, HandoffListItem]
    ] = Factory(
        ResolveHandoffUseCase,
        handoff_repo=repositories.handoff_repo,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_handoffs_use_case: Factory[UseCaseContract[ListHandoffsQuery, HandoffPage]] = (
        Factory(
            ListHandoffsUseCase,
            business_repo=repositories.business_repo,
            handoff_repo=repositories.handoff_repo,
            contact_repo=repositories.contact_repo,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    record_unanswered_question_use_case: Factory[
        UseCaseContract[RecordUnansweredQuestionCommand, UnansweredQuestionView]
    ] = Factory(
        RecordUnansweredQuestionUseCase,
        business_repo=repositories.business_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_unanswered_questions_use_case: Factory[
        UseCaseContract[ListUnansweredQuestionsQuery, UnansweredQuestionPage]
    ] = Factory(
        ListUnansweredQuestionsUseCase,
        unanswered_question_repo=repositories.unanswered_question_repo,
    )
    answer_unanswered_question_use_case: Factory[
        UseCaseContract[AnswerUnansweredQuestionCommand, AnsweredQuestionResult]
    ] = Factory(
        AnswerUnansweredQuestionUseCase,
        unanswered_question_repo=repositories.unanswered_question_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_dashboard_stats_use_case: Factory[
        UseCaseContract[DashboardStatsQuery, DashboardStats]
    ] = Factory(
        GetDashboardStatsUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        usage_event_repo=repositories.usage_event_repo,
        subscription_repo=repositories.subscription_repo,
        plan_registry=registries.plan_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Google Calendar.
    start_google_calendar_connection_use_case: Factory[
        UseCaseContract[StartCalendarConnectionCommand, CalendarConnectUrlView]
    ] = Factory(
        StartGoogleCalendarConnectionUseCase,
        business_repo=repositories.business_repo,
        authorization_state_repo=repositories.calendar_authorization_state_repo,
        calendar_client=clients.google_calendar_client,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    complete_google_calendar_connection_use_case: Factory[
        UseCaseContract[CompleteCalendarConnectionCommand, CalendarConnectionOutcome]
    ] = Factory(
        CompleteGoogleCalendarConnectionUseCase,
        authorization_state_repo=repositories.calendar_authorization_state_repo,
        connection_repo=repositories.calendar_connection_repo,
        calendar_client=clients.google_calendar_client,
        secret_cipher=adapters.secret_cipher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    disconnect_google_calendar_use_case: Factory[
        UseCaseContract[DisconnectCalendarCommand, CalendarDisconnectResult]
    ] = Factory(
        DisconnectGoogleCalendarUseCase,
        connection_repo=repositories.calendar_connection_repo,
        event_link_repo=repositories.calendar_event_link_repo,
        calendar_client=clients.google_calendar_client,
        secret_cipher=adapters.secret_cipher,
    )
    get_google_calendar_connection_use_case: Factory[
        UseCaseContract[CalendarConnectionStatusQuery, CalendarConnectionStatusView]
    ] = Factory(
        GetGoogleCalendarConnectionUseCase,
        connection_repo=repositories.calendar_connection_repo,
        calendar_client=clients.google_calendar_client,
    )

    # --- Conversation engine: the ten tools, then prepare, generate, record.
    run_assistant_tool_use_case: Factory[
        UseCaseContract[AssistantToolInvocation, AssistantToolOutcome]
    ] = Factory(
        RunAssistantToolUseCase,
        search_knowledge=search_knowledge_use_case,
        get_price=get_price_use_case,
        send_link=send_link_use_case,
        check_availability=check_availability_use_case,
        create_booking=create_booking_use_case,
        cancel_booking=cancel_booking_use_case,
        reschedule_booking=reschedule_booking_use_case,
        create_lead=create_lead_use_case,
        handoff_to_human=handoff_to_human_use_case,
        record_unanswered_question=record_unanswered_question_use_case,
        phone_number_parser=utilities.phone_number_parser,
    )
    prepare_conversation_turn_use_case: Factory[
        UseCaseContract[InboundMessage, PreparedTurn]
    ] = Factory(
        PrepareConversationTurnUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        language_detector=utilities.language_detector,
        wall_clock=time_provider.microsecond_wall_clock,
        contact_message_limit=config.app_settings.provided.contact_message_limit_per_hour,
    )
    generate_assistant_reply_use_case: Factory[
        UseCaseContract[PreparedTurn, GeneratedReply]
    ] = Factory(
        GenerateAssistantReplyUseCase,
        llm_adapter=adapters.llm_adapter,
        llm_turn_repo=repositories.llm_turn_repo,
        message_repo=repositories.message_repo,
        tool_registry=registries.assistant_tool_registry,
        run_assistant_tool=run_assistant_tool_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
        max_output_tokens=config.app_settings.provided.llm_max_output_tokens,
        effort=config.app_settings.provided.llm_chat_effort,
        tool_round_limit=config.app_settings.provided.llm_tool_round_limit,
    )
    record_assistant_reply_use_case: Factory[
        UseCaseContract[ReplyRecord, AssistantReply]
    ] = Factory(
        RecordAssistantReplyUseCase,
        message_repo=repositories.message_repo,
        conversation_repo=repositories.conversation_repo,
        usage_event_repo=repositories.usage_event_repo,
        localized_text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    open_voice_conversation_use_case: Factory[
        UseCaseContract[VoiceToolCallRequest, AssistantToolContext]
    ] = Factory(
        OpenVoiceConversationUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        channel_repo=repositories.channel_repo,
        plan_registry=registries.plan_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_voice_tool_call_use_case: Factory[
        UseCaseContract[VoiceToolCallRecord, VoiceToolCallResult]
    ] = Factory(
        RecordVoiceToolCallUseCase,
        message_repo=repositories.message_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    build_call_greeting_use_case: Factory[
        UseCaseContract[CallGreetingRequest, CallGreeting]
    ] = Factory(
        BuildCallGreetingUseCase,
        business_repo=repositories.business_repo,
        localized_text_resolver=utilities.localized_text_resolver,
    )

    # --- Conversation feed, owner test chat and menu import.
    list_conversations_use_case: Factory[
        UseCaseContract[ConversationListQuery, ConversationPage]
    ] = Factory(
        ListConversationsUseCase,
        authorize_business_access=authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        summary_transformer=transformers.conversation_summary_transformer,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_conversation_use_case: Factory[
        UseCaseContract[ConversationQuery, ConversationDetailView]
    ] = Factory(
        GetConversationUseCase,
        authorize_business_access=authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        audit_log_repo=repositories.audit_log_repo,
        summary_transformer=transformers.conversation_summary_transformer,
        message_transformer=transformers.message_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        call_repo=repositories.call_repo,
        call_transformer=transformers.call_view_transformer,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        resource_repo=repositories.resource_repo,
        channel_repo=repositories.channel_repo,
    )
    get_call_recording_use_case: Factory[
        UseCaseContract[CallRecordingQuery, RecordingAudio]
    ] = Factory(
        GetCallRecordingUseCase,
        authorize_business_access=authorize_business_access_use_case,
        call_repo=repositories.call_repo,
        recording_storage=adapters.recording_storage,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_staff_message_use_case: Factory[
        UseCaseContract[SendStaffMessageCommand, StaffMessageResult]
    ] = Factory(
        SendStaffMessageUseCase,
        authorize_business_access=authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        channel_message_sender=facilitators.channel_message_sender,
        message_transformer=transformers.message_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    rate_conversation_use_case: Factory[
        UseCaseContract[RateConversationCommand, ConversationSummaryView]
    ] = Factory(
        RateConversationUseCase,
        authorize_business_access=authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        summary_transformer=transformers.conversation_summary_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resolve_test_chat_version_use_case: Factory[
        UseCaseContract[OwnerTestChatVersionQuery, AssistantVersionId]
    ] = Factory(
        ResolveTestChatVersionUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
    )
    import_menu_use_case: Factory[
        UseCaseContract[ImportMenuCommand, MenuImportResult]
    ] = Factory(
        ImportMenuUseCase,
        authorize_business_access=authorize_business_access_use_case,
        menu_extraction_adapter=adapters.menu_extraction_adapter,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    confirm_imported_items_use_case: Factory[
        UseCaseContract[ConfirmImportedItemsCommand, ConfirmImportedItemsResult]
    ] = Factory(
        ConfirmImportedItemsUseCase,
        authorize_business_access=authorize_business_access_use_case,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    discard_import_batch_use_case: Factory[
        UseCaseContract[DiscardImportBatchCommand, DiscardedImportBatch]
    ] = Factory(
        DiscardImportBatchUseCase,
        authorize_business_access=authorize_business_access_use_case,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )

    # --- Assistant assembly, autotests and publishing (the autotest scenario
    #     runner needs the conversation orchestrator: OrchestratorsContainer).
    assemble_assistant_version_use_case: Factory[
        UseCaseContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        AssembleAssistantVersionUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        niche_template_registry=registries.niche_template_registry,
        plan_registry=registries.plan_registry,
        business_facts_transformer=transformers.business_facts_transformer,
        assistant_instruction_transformer=transformers.assistant_instruction_transformer,
        version_details_transformer=transformers.assistant_version_details_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_assistant_versions_use_case: Factory[
        UseCaseContract[AssistantVersionsQuery, list[AssistantVersionSummary]]
    ] = Factory(
        ListAssistantVersionsUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        version_summary_transformer=transformers.assistant_version_summary_transformer,
    )
    get_assistant_version_use_case: Factory[
        UseCaseContract[AssistantVersionQuery, AssistantVersionDetails]
    ] = Factory(
        GetAssistantVersionUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        version_details_transformer=transformers.assistant_version_details_transformer,
    )
    plan_autotest_scenarios_use_case: Factory[
        UseCaseContract[AutotestPlanningRequest, AutotestScenarioPlanning]
    ] = Factory(
        PlanAutotestScenariosUseCase,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        language_registry=registries.language_registry,
    )
    start_autotest_run_use_case: Factory[
        UseCaseContract[RunAutotestsCommand, AutotestRunPlan]
    ] = Factory(
        StartAutotestRunUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        plan_autotest_scenarios=plan_autotest_scenarios_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    enqueue_autotest_run_use_case: Factory[
        UseCaseContract[AutotestRunPlan, AutotestRunView]
    ] = Factory(
        EnqueueAutotestRunUseCase,
        autotest_run_repo=repositories.autotest_run_repo,
        job_queue=facilitators.job_queue_facilitator,
        autotest_run_view_transformer=transformers.autotest_run_view_transformer,
    )
    resume_autotest_run_use_case: Factory[
        UseCaseContract[QueuedJobInput, AutotestRunPlan]
    ] = Factory(
        ResumeAutotestRunUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        plan_autotest_scenarios=plan_autotest_scenarios_use_case,
    )
    abandon_autotest_run_use_case: Factory[
        UseCaseContract[AutotestRunFailure, None]
    ] = Factory(
        AbandonAutotestRunUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_autotest_progress_use_case: Factory[
        UseCaseContract[AutotestRunProgress, None]
    ] = Factory(
        RecordAutotestProgressUseCase,
        autotest_run_repo=repositories.autotest_run_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    finish_autotest_run_use_case: Factory[
        UseCaseContract[AutotestRunCompletion, AutotestRunView]
    ] = Factory(
        FinishAutotestRunUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        autotest_run_view_transformer=transformers.autotest_run_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_autotest_run_use_case: Factory[
        UseCaseContract[AssistantVersionQuery, AutotestRunView]
    ] = Factory(
        GetAutotestRunUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        autotest_run_view_transformer=transformers.autotest_run_view_transformer,
    )
    check_go_live_readiness_use_case: Factory[
        UseCaseContract[GoLiveReadinessRequest, GoLiveReadiness]
    ] = Factory(
        CheckGoLiveReadinessUseCase,
        subscription_repo=repositories.subscription_repo,
        dpa_acceptance_repo=repositories.dpa_acceptance_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        niche_template_registry=registries.niche_template_registry,
        voice_agent_provisioner=adapters.voice_agent_provisioner,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_go_live_readiness_use_case: Factory[
        UseCaseContract[AssistantVersionQuery, GoLiveReadiness]
    ] = Factory(
        GetGoLiveReadinessUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        check_go_live_readiness=check_go_live_readiness_use_case,
    )
    activate_assistant_version_use_case: Factory[
        UseCaseContract[AssistantVersionActivation, AssistantVersionDocument]
    ] = Factory(
        ActivateAssistantVersionUseCase,
        check_go_live_readiness=check_go_live_readiness_use_case,
        remove_voice_agent=remove_voice_agent_use_case,
        business_profile_repo=repositories.business_profile_repo,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        voice_agent_provisioner=adapters.voice_agent_provisioner,
        build_call_greeting=build_call_greeting_use_case,
        assistant_tool_catalog=registries.assistant_tool_registry,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resume_assistant_use_case: Factory[UseCaseContract[BusinessDocument, None]] = (
        Factory(
            ResumeAssistantUseCase,
            assistant_version_repo=repositories.assistant_version_repo,
            activate_assistant_version=activate_assistant_version_use_case,
        )
    )
    update_business_settings_use_case: Factory[
        UseCaseContract[UpdateBusinessSettingsCommand, BusinessView]
    ] = Factory(
        UpdateBusinessSettingsUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        subscription_repo=repositories.subscription_repo,
        language_registry=registries.language_registry,
        phone_number_parser=utilities.phone_number_parser,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        remove_voice_agent=remove_voice_agent_use_case,
        resume_assistant=resume_assistant_use_case,
    )
    publish_assistant_version_use_case: Factory[
        UseCaseContract[PublishAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        PublishAssistantVersionUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        check_go_live_readiness=check_go_live_readiness_use_case,
        activate_assistant_version=activate_assistant_version_use_case,
        version_details_transformer=transformers.assistant_version_details_transformer,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    rollback_assistant_version_use_case: Factory[
        UseCaseContract[RollbackAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        RollbackAssistantVersionUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        activate_assistant_version=activate_assistant_version_use_case,
        version_details_transformer=transformers.assistant_version_details_transformer,
    )

    # --- Channels: webhooks, replies, cabinet settings, widget, staff links.
    receive_telegram_webhook_use_case: Factory[
        UseCaseContract[TelegramWebhookRequest, list[ChannelInboundDelivery]]
    ] = Factory(
        ReceiveTelegramWebhookUseCase,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_adapter=adapters.telegram_channel_adapter,
        receipt_repo=repositories.channel_message_receipt_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    receive_meta_webhook_use_case: Factory[
        UseCaseContract[MetaWebhookRequest, list[ChannelInboundDelivery]]
    ] = Factory(
        ReceiveMetaWebhookUseCase,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        whatsapp_adapter=adapters.whatsapp_channel_adapter,
        messenger_adapter=adapters.messenger_channel_adapter,
        instagram_adapter=adapters.instagram_channel_adapter,
        receipt_repo=repositories.channel_message_receipt_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    deliver_channel_reply_use_case: Factory[
        UseCaseContract[ChannelReplyDelivery, DeliveredMessageCount]
    ] = Factory(
        DeliverChannelReplyUseCase,
        telegram_adapter=adapters.telegram_channel_adapter,
        whatsapp_adapter=adapters.whatsapp_channel_adapter,
        messenger_adapter=adapters.messenger_channel_adapter,
        instagram_adapter=adapters.instagram_channel_adapter,
        usage_event_repo=repositories.usage_event_repo,
        channel_repo=repositories.channel_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    verify_meta_webhook_use_case: Factory[
        UseCaseContract[MetaWebhookVerificationRequest, MetaWebhookChallenge]
    ] = Factory(
        VerifyMetaWebhookUseCase,
        app_settings=config.app_settings,
    )
    connect_channel_use_case: Factory[
        UseCaseContract[ConnectChannelCommand, ChannelView]
    ] = Factory(
        ConnectChannelUseCase,
        authorize_business_access=authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_client=clients.telegram_bot_client,
        meta_client=clients.meta_graph_client,
        phone_number_parser=utilities.phone_number_parser,
        audit_log_repo=repositories.audit_log_repo,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        storage_scope=utilities.storage_scope,
    )
    set_whatsapp_staff_template_use_case: Factory[
        UseCaseContract[SetWhatsAppStaffTemplateCommand, ChannelView]
    ] = Factory(
        SetWhatsAppStaffTemplateUseCase,
        authorize_business_access=authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    disable_channel_use_case: Factory[
        UseCaseContract[DisableChannelCommand, ChannelView]
    ] = Factory(
        DisableChannelUseCase,
        authorize_business_access=authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_client=clients.telegram_bot_client,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        remove_voice_agent=remove_voice_agent_use_case,
    )
    list_channels_use_case: Factory[
        UseCaseContract[ChannelListQuery, list[ChannelView]]
    ] = Factory(
        ListChannelsUseCase,
        authorize_business_access=authorize_business_access_use_case,
        channel_repo=repositories.channel_repo,
    )
    get_widget_config_use_case: Factory[
        UseCaseContract[BusinessId, WidgetConfigView]
    ] = Factory(
        GetWidgetConfigUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        language_registry=registries.language_registry,
    )
    get_widget_messages_use_case: Factory[
        UseCaseContract[WidgetMessagesQuery, WidgetMessagesView]
    ] = Factory(
        GetWidgetMessagesUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        language_registry=registries.language_registry,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    accept_widget_message_use_case: Factory[
        UseCaseContract[WidgetMessageCommand, InboundMessage]
    ] = Factory(
        AcceptWidgetMessageUseCase,
        business_repo=repositories.business_repo,
        channel_repo=repositories.channel_repo,
    )
    build_widget_reply_use_case: Factory[
        UseCaseContract[WidgetReplyInput, WidgetReplyView]
    ] = Factory(
        BuildWidgetReplyUseCase,
        message_repo=repositories.message_repo,
        language_registry=registries.language_registry,
    )
    get_widget_snippet_use_case: Factory[
        UseCaseContract[WidgetSnippetQuery, WidgetSnippetView]
    ] = Factory(
        GetWidgetSnippetUseCase,
        authorize_business_access=authorize_business_access_use_case,
        app_settings=config.app_settings,
    )
    # Singleton: it caches the platform bot's username.
    create_telegram_link_use_case: Singleton[
        UseCaseContract[CreateTelegramLinkCommand, TelegramLinkView]
    ] = Singleton(
        CreateTelegramLinkUseCase,
        authorize_business_access=authorize_business_access_use_case,
        link_repo=repositories.manager_telegram_link_repo,
        language_registry=registries.language_registry,
        telegram_client=clients.telegram_bot_client,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    handle_platform_bot_update_use_case: Factory[
        UseCaseContract[PlatformBotWebhookRequest, PlatformBotWebhookOutcome]
    ] = Factory(
        HandlePlatformBotUpdateUseCase,
        link_repo=repositories.manager_telegram_link_repo,
        business_repo=repositories.business_repo,
        audit_log_repo=repositories.audit_log_repo,
        telegram_client=clients.telegram_bot_client,
        text_resolver=utilities.localized_text_resolver,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    configure_platform_bot_webhook_use_case: Factory[
        UseCaseContract[PlatformBotWebhookSetup, TelegramBotProfile]
    ] = Factory(
        ConfigurePlatformBotWebhookUseCase,
        telegram_client=clients.telegram_bot_client,
        app_settings=config.app_settings,
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
        wall_clock=time_provider.microsecond_wall_clock,
        voice_webhook_adapter=adapters.voice_webhook_adapter,
        phone_number_parser=utilities.phone_number_parser,
        build_call_greeting=build_call_greeting_use_case,
        app_settings=config.app_settings,
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
    send_call_confirmation_use_case: Factory[UseCaseContract[RecordedCall, bool]] = (
        Factory(
            SendCallConfirmationUseCase,
            business_repo=repositories.business_repo,
            booking_repo=repositories.booking_repo,
            contact_repo=repositories.contact_repo,
            channel_repo=repositories.channel_repo,
            channel_message_sender=facilitators.channel_message_sender,
            text_resolver=utilities.localized_text_resolver,
        )
    )

    # --- Billing: subscriptions, invoices, checkout, webhook, periodic jobs.
    issue_due_invoices_use_case: Factory[
        UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]]
    ] = Factory(
        IssueDueInvoicesUseCase,
        invoice_repo=repositories.invoice_repo,
        plan_registry=registries.plan_registry,
        invoice_description_transformer=transformers.invoice_description_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    assemble_billing_overview_use_case: Factory[
        UseCaseContract[BillingOverviewSource, BillingOverview]
    ] = Factory(
        AssembleBillingOverviewUseCase,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        usage_event_repo=repositories.usage_event_repo,
        plan_registry=registries.plan_registry,
        exchange_rate_registry=registries.exchange_rate_registry,
        localized_text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_billing_overview_use_case: Factory[
        UseCaseContract[BillingOverviewQuery, BillingOverview]
    ] = Factory(
        GetBillingOverviewUseCase,
        authorize_business_access=authorize_business_access_use_case,
        assemble_billing_overview=assemble_billing_overview_use_case,
    )
    start_trial_use_case: Factory[
        UseCaseContract[StartTrialCommand, BillingOverview]
    ] = Factory(
        StartTrialUseCase,
        authorize_business_access=authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        assemble_billing_overview=assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    change_plan_use_case: Factory[
        UseCaseContract[ChangePlanCommand, BillingOverview]
    ] = Factory(
        ChangePlanUseCase,
        authorize_business_access=authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        payment_gateway=adapters.payment_gateway,
        assemble_billing_overview=assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
        remove_voice_agent=remove_voice_agent_use_case,
    )
    cancel_subscription_use_case: Factory[
        UseCaseContract[CancelSubscriptionCommand, BillingOverview]
    ] = Factory(
        CancelSubscriptionUseCase,
        authorize_business_access=authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        payment_gateway=adapters.payment_gateway,
        assemble_billing_overview=assemble_billing_overview_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    start_checkout_use_case: Factory[
        UseCaseContract[StartCheckoutCommand, CheckoutSessionView]
    ] = Factory(
        StartCheckoutUseCase,
        authorize_business_access=authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        payment_order_repo=repositories.payment_order_repo,
        issue_due_invoices=issue_due_invoices_use_case,
        payment_gateway=adapters.payment_gateway,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    open_subscription_use_case: Factory[
        UseCaseContract[SubscribeCommand, SubscriptionOpening]
    ] = Factory(
        OpenSubscriptionUseCase,
        authorize_business_access=authorize_business_access_use_case,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    process_payment_webhook_use_case: Factory[
        UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]
    ] = Factory(
        ProcessPaymentWebhookUseCase,
        payment_gateway=adapters.payment_gateway,
        payment_order_repo=repositories.payment_order_repo,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        plan_registry=registries.plan_registry,
        issue_due_invoices=issue_due_invoices_use_case,
        manager_notifier=facilitators.manager_notification_facilitator,
        billing_notice_transformer=transformers.billing_notice_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    end_trials_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        EndTrialsUseCase,
        business_repo=repositories.business_repo,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        user_repo=repositories.user_repo,
        plan_registry=registries.plan_registry,
        issue_due_invoices=issue_due_invoices_use_case,
        manager_notifier=facilitators.manager_notification_facilitator,
        billing_notice_transformer=transformers.billing_notice_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    enforce_grace_periods_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            EnforceGracePeriodsUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            user_repo=repositories.user_repo,
            plan_registry=registries.plan_registry,
            issue_due_invoices=issue_due_invoices_use_case,
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    check_package_usage_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            CheckPackageUsageUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            usage_event_repo=repositories.usage_event_repo,
            package_usage_warning_repo=repositories.package_usage_warning_repo,
            user_repo=repositories.user_repo,
            plan_registry=registries.plan_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    invoice_usage_overage_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            InvoiceUsageOverageUseCase,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            usage_event_repo=repositories.usage_event_repo,
            user_repo=repositories.user_repo,
            plan_registry=registries.plan_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            invoice_description_transformer=(
                transformers.invoice_description_transformer
            ),
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    compute_client_cost_use_case: Factory[
        UseCaseContract[ClientCostQuery, ClientCostReport]
    ] = Factory(
        ComputeClientCostUseCase,
        business_repo=repositories.business_repo,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        usage_event_repo=repositories.usage_event_repo,
        message_repo=repositories.message_repo,
        exchange_rate_registry=registries.exchange_rate_registry,
    )

    # --- Platform admin.
    authorize_platform_admin_use_case: Factory[
        UseCaseContract[UserId, UserDocument]
    ] = Factory(
        AuthorizePlatformAdminUseCase,
        user_repo=repositories.user_repo,
    )
    summarize_client_use_case: Factory[
        UseCaseContract[ClientSummarySource, AdminClientSummary]
    ] = Factory(
        SummarizeClientUseCase,
        subscription_repo=repositories.subscription_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        handoff_repo=repositories.handoff_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        message_repo=repositories.message_repo,
        usage_event_repo=repositories.usage_event_repo,
        plan_registry=registries.plan_registry,
        compute_client_cost=compute_client_cost_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_clients_use_case: Factory[
        UseCaseContract[AdminClientsQuery, AdminClientPage]
    ] = Factory(
        ListClientsUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        summarize_client=summarize_client_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_client_health_use_case: Factory[
        UseCaseContract[AdminClientQuery, ClientHealthView]
    ] = Factory(
        GetClientHealthUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        invoice_repo=repositories.invoice_repo,
        payment_order_repo=repositories.payment_order_repo,
        summarize_client=summarize_client_use_case,
    )
    open_client_cabinet_use_case: Factory[
        UseCaseContract[OpenClientCabinetCommand, ClientCabinetAccess]
    ] = Factory(
        OpenClientCabinetUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Observability.
    flush_llm_traces_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        FlushLlmTracesUseCase,
        trace_facilitator=adapters.llm_trace_facilitator,
    )

    # --- Template example (keeps its concrete type).
    example_use_case: Factory[ExampleUseCase] = Factory(ExampleUseCase)

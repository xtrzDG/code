from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.orchestrators import OrchestratorsContainer
from app.containers.provider_chains import orchestrator_pipeline
from app.containers.use_cases import UseCasesContainer
from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.orchestrators.channels.channel_webhook_orchestrator import (
    ChannelWebhookOrchestrator,
)
from app.orchestrators.channels.widget_message_orchestrator import (
    WidgetMessageOrchestrator,
)
from app.pipelines.assistants.assemble_assistant_version_pipeline import (
    AssembleAssistantVersionPipeline,
)
from app.pipelines.conversations.customer_message_pipeline import (
    CustomerMessagePipeline,
)
from app.pipelines.conversations.owner_test_chat_pipeline import (
    OwnerTestChatPipeline,
)
from app.schemas.dto.assistants import (
    AssembleAssistantVersionCommand,
    AssistantVersionDetails,
)
from app.schemas.dto.channels import (
    ChannelWebhookOutcome,
    MetaWebhookRequest,
    TelegramWebhookRequest,
    WidgetMessageCommand,
    WidgetReplyView,
)
from app.schemas.dto.conversation_feed import OwnerTestChatCommand
from app.schemas.dto.conversations import AssistantReply


class PipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines: the generic one around each orchestrator and the dedicated
    phases (assembly then autotests, the customer message, the owner's test
    chat).

    The channel webhook and widget orchestrators hand every customer message
    to the customer-message pipeline, so they are wired here, after it.
    """

    orchestrators: OrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]
    use_cases: UseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Customer messages of every channel. Singleton: its per-customer
    # locks must be shared by every channel of the process.
    customer_message_pipeline: Singleton[CustomerMessagePipelineContract] = Singleton(
        CustomerMessagePipeline,
        turn_orchestrator=orchestrators.conversation_turn_orchestrator,
    )
    owner_test_chat_pipeline: Factory[
        PipelineContract[OwnerTestChatCommand, AssistantReply]
    ] = Factory(
        OwnerTestChatPipeline,
        prepare_test_message=orchestrators.owner_test_chat_orchestrator,
        turn_orchestrator=orchestrators.conversation_turn_orchestrator,
    )
    assemble_assistant_version_pipeline: Factory[
        PipelineContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        AssembleAssistantVersionPipeline,
        assemble_assistant_version=orchestrators.assemble_assistant_version_orchestrator,
        run_autotests=orchestrators.queue_autotest_run_orchestrator,
        get_assistant_version=orchestrators.get_assistant_version_orchestrator,
    )

    # --- Messaging webhooks and the website widget.
    telegram_webhook_orchestrator: Factory[
        OrchestratorContract[TelegramWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[TelegramWebhookRequest],
        receive_webhook=use_cases.receive_telegram_webhook_use_case,
        customer_message_pipeline=customer_message_pipeline,
        deliver_reply=use_cases.deliver_channel_reply_use_case,
    )
    meta_webhook_orchestrator: Factory[
        OrchestratorContract[MetaWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[MetaWebhookRequest],
        receive_webhook=use_cases.receive_meta_webhook_use_case,
        customer_message_pipeline=customer_message_pipeline,
        deliver_reply=use_cases.deliver_channel_reply_use_case,
    )
    widget_message_orchestrator: Factory[
        OrchestratorContract[WidgetMessageCommand, WidgetReplyView]
    ] = Factory(
        WidgetMessageOrchestrator,
        accept_widget_message=use_cases.accept_widget_message_use_case,
        customer_message_pipeline=customer_message_pipeline,
        build_widget_reply=use_cases.build_widget_reply_use_case,
    )
    telegram_webhook_pipeline = orchestrator_pipeline(telegram_webhook_orchestrator)
    meta_webhook_pipeline = orchestrator_pipeline(meta_webhook_orchestrator)
    widget_message_pipeline = orchestrator_pipeline(widget_message_orchestrator)

    # --- Dedicated orchestrators.
    call_forwarding_instructions_pipeline = orchestrator_pipeline(
        orchestrators.call_forwarding_instructions_orchestrator
    )
    run_autotests_pipeline = orchestrator_pipeline(
        orchestrators.queue_autotest_run_orchestrator
    )
    run_queued_autotests_pipeline = orchestrator_pipeline(
        orchestrators.run_queued_autotests_orchestrator
    )
    voice_tool_webhook_pipeline = orchestrator_pipeline(
        orchestrators.voice_tool_webhook_orchestrator
    )
    post_call_webhook_pipeline = orchestrator_pipeline(
        orchestrators.post_call_webhook_orchestrator
    )
    purge_expired_recordings_pipeline = orchestrator_pipeline(
        orchestrators.purge_expired_recordings_job_orchestrator
    )

    # --- One orchestrator per endpoint or job.

    # --- Catalog.
    list_countries_pipeline = orchestrator_pipeline(
        orchestrators.list_countries_orchestrator
    )
    get_country_profile_pipeline = orchestrator_pipeline(
        orchestrators.get_country_profile_orchestrator
    )
    list_languages_pipeline = orchestrator_pipeline(
        orchestrators.list_languages_orchestrator
    )
    quote_plans_pipeline = orchestrator_pipeline(orchestrators.quote_plans_orchestrator)
    parse_phone_number_pipeline = orchestrator_pipeline(
        orchestrators.parse_phone_number_orchestrator
    )

    # --- Sign-in and the current user.
    authenticate_user_pipeline = orchestrator_pipeline(
        orchestrators.authenticate_user_orchestrator
    )
    start_otp_login_pipeline = orchestrator_pipeline(
        orchestrators.start_otp_login_orchestrator
    )
    verify_otp_login_pipeline = orchestrator_pipeline(
        orchestrators.verify_otp_login_orchestrator
    )
    logout_pipeline = orchestrator_pipeline(orchestrators.logout_orchestrator)
    get_current_user_pipeline = orchestrator_pipeline(
        orchestrators.get_current_user_orchestrator
    )
    update_current_user_pipeline = orchestrator_pipeline(
        orchestrators.update_current_user_orchestrator
    )

    # --- Businesses and teams.
    authorize_business_access_pipeline = orchestrator_pipeline(
        orchestrators.authorize_business_access_orchestrator
    )
    create_business_pipeline = orchestrator_pipeline(
        orchestrators.create_business_orchestrator
    )
    list_my_businesses_pipeline = orchestrator_pipeline(
        orchestrators.list_my_businesses_orchestrator
    )
    get_business_pipeline = orchestrator_pipeline(
        orchestrators.get_business_orchestrator
    )
    update_business_settings_pipeline = orchestrator_pipeline(
        orchestrators.update_business_settings_orchestrator
    )
    invite_staff_pipeline = orchestrator_pipeline(
        orchestrators.invite_staff_orchestrator
    )
    remove_member_pipeline = orchestrator_pipeline(
        orchestrators.remove_member_orchestrator
    )

    # --- Compliance.
    get_dpa_status_pipeline = orchestrator_pipeline(
        orchestrators.get_dpa_status_orchestrator
    )
    accept_dpa_pipeline = orchestrator_pipeline(orchestrators.accept_dpa_orchestrator)
    list_audit_log_pipeline = orchestrator_pipeline(
        orchestrators.list_audit_log_orchestrator
    )
    export_contact_data_pipeline = orchestrator_pipeline(
        orchestrators.export_contact_data_orchestrator
    )
    delete_contact_data_pipeline = orchestrator_pipeline(
        orchestrators.delete_contact_data_orchestrator
    )

    # --- Niche templates and the profile wizard.
    list_niche_templates_pipeline = orchestrator_pipeline(
        orchestrators.list_niche_templates_orchestrator
    )
    get_niche_template_pipeline = orchestrator_pipeline(
        orchestrators.get_niche_template_orchestrator
    )
    get_profile_wizard_pipeline = orchestrator_pipeline(
        orchestrators.get_profile_wizard_orchestrator
    )
    get_business_profile_pipeline = orchestrator_pipeline(
        orchestrators.get_business_profile_orchestrator
    )
    save_profile_pipeline = orchestrator_pipeline(
        orchestrators.save_profile_orchestrator
    )
    save_profile_step_pipeline = orchestrator_pipeline(
        orchestrators.save_profile_step_orchestrator
    )
    compute_profile_gaps_pipeline = orchestrator_pipeline(
        orchestrators.compute_profile_gaps_orchestrator
    )

    # --- Knowledge base.
    list_knowledge_items_pipeline = orchestrator_pipeline(
        orchestrators.list_knowledge_items_orchestrator
    )
    create_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.create_knowledge_item_orchestrator
    )
    get_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.get_knowledge_item_orchestrator
    )
    update_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.update_knowledge_item_orchestrator
    )
    delete_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.delete_knowledge_item_orchestrator
    )
    search_knowledge_pipeline = orchestrator_pipeline(
        orchestrators.search_knowledge_orchestrator
    )

    # --- Resources and schedule exceptions.
    list_resources_pipeline = orchestrator_pipeline(
        orchestrators.list_resources_orchestrator
    )
    create_resource_pipeline = orchestrator_pipeline(
        orchestrators.create_resource_orchestrator
    )
    update_resource_pipeline = orchestrator_pipeline(
        orchestrators.update_resource_orchestrator
    )
    list_schedule_exceptions_pipeline = orchestrator_pipeline(
        orchestrators.list_schedule_exceptions_orchestrator
    )
    create_schedule_exception_pipeline = orchestrator_pipeline(
        orchestrators.create_schedule_exception_orchestrator
    )
    delete_schedule_exception_pipeline = orchestrator_pipeline(
        orchestrators.delete_schedule_exception_orchestrator
    )

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_pipeline = orchestrator_pipeline(
        orchestrators.check_availability_orchestrator
    )
    list_bookings_pipeline = orchestrator_pipeline(
        orchestrators.list_bookings_orchestrator
    )
    create_manual_booking_pipeline = orchestrator_pipeline(
        orchestrators.create_manual_booking_orchestrator
    )
    cancel_booking_pipeline = orchestrator_pipeline(
        orchestrators.cancel_booking_orchestrator
    )
    reschedule_booking_pipeline = orchestrator_pipeline(
        orchestrators.reschedule_booking_orchestrator
    )
    update_booking_status_pipeline = orchestrator_pipeline(
        orchestrators.update_booking_status_orchestrator
    )
    list_leads_pipeline = orchestrator_pipeline(orchestrators.list_leads_orchestrator)
    update_lead_status_pipeline = orchestrator_pipeline(
        orchestrators.update_lead_status_orchestrator
    )
    list_handoffs_pipeline = orchestrator_pipeline(
        orchestrators.list_handoffs_orchestrator
    )
    resolve_handoff_pipeline = orchestrator_pipeline(
        orchestrators.resolve_handoff_orchestrator
    )
    list_unanswered_questions_pipeline = orchestrator_pipeline(
        orchestrators.list_unanswered_questions_orchestrator
    )
    answer_unanswered_question_pipeline = orchestrator_pipeline(
        orchestrators.answer_unanswered_question_orchestrator
    )
    get_dashboard_stats_pipeline = orchestrator_pipeline(
        orchestrators.get_dashboard_stats_orchestrator
    )
    start_google_calendar_connection_pipeline = orchestrator_pipeline(
        orchestrators.start_google_calendar_connection_orchestrator
    )
    complete_google_calendar_connection_pipeline = orchestrator_pipeline(
        orchestrators.complete_google_calendar_connection_orchestrator
    )
    disconnect_google_calendar_pipeline = orchestrator_pipeline(
        orchestrators.disconnect_google_calendar_orchestrator
    )

    # --- Conversation feed and menu import.
    list_conversations_pipeline = orchestrator_pipeline(
        orchestrators.list_conversations_orchestrator
    )
    get_conversation_pipeline = orchestrator_pipeline(
        orchestrators.get_conversation_orchestrator
    )
    rate_conversation_pipeline = orchestrator_pipeline(
        orchestrators.rate_conversation_orchestrator
    )
    import_menu_pipeline = orchestrator_pipeline(orchestrators.import_menu_orchestrator)
    confirm_imported_items_pipeline = orchestrator_pipeline(
        orchestrators.confirm_imported_items_orchestrator
    )
    discard_import_batch_pipeline = orchestrator_pipeline(
        orchestrators.discard_import_batch_orchestrator
    )

    # --- Assistant versions and autotests.
    list_assistant_versions_pipeline = orchestrator_pipeline(
        orchestrators.list_assistant_versions_orchestrator
    )
    get_assistant_version_pipeline = orchestrator_pipeline(
        orchestrators.get_assistant_version_orchestrator
    )
    get_autotest_run_pipeline = orchestrator_pipeline(
        orchestrators.get_autotest_run_orchestrator
    )
    get_go_live_readiness_pipeline = orchestrator_pipeline(
        orchestrators.get_go_live_readiness_orchestrator
    )
    publish_assistant_version_pipeline = orchestrator_pipeline(
        orchestrators.publish_assistant_version_orchestrator
    )
    rollback_assistant_version_pipeline = orchestrator_pipeline(
        orchestrators.rollback_assistant_version_orchestrator
    )

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_pipeline = orchestrator_pipeline(
        orchestrators.verify_meta_webhook_orchestrator
    )
    handle_platform_bot_update_pipeline = orchestrator_pipeline(
        orchestrators.handle_platform_bot_update_orchestrator
    )
    get_widget_config_pipeline = orchestrator_pipeline(
        orchestrators.get_widget_config_orchestrator
    )
    list_channels_pipeline = orchestrator_pipeline(
        orchestrators.list_channels_orchestrator
    )
    connect_channel_pipeline = orchestrator_pipeline(
        orchestrators.connect_channel_orchestrator
    )
    disable_channel_pipeline = orchestrator_pipeline(
        orchestrators.disable_channel_orchestrator
    )
    get_widget_snippet_pipeline = orchestrator_pipeline(
        orchestrators.get_widget_snippet_orchestrator
    )
    create_telegram_link_pipeline = orchestrator_pipeline(
        orchestrators.create_telegram_link_orchestrator
    )
    configure_platform_bot_webhook_pipeline = orchestrator_pipeline(
        orchestrators.configure_platform_bot_webhook_orchestrator
    )

    # --- Voice webhooks.
    start_voice_call_pipeline = orchestrator_pipeline(
        orchestrators.start_voice_call_orchestrator
    )

    # --- Billing and payments.
    get_billing_overview_pipeline = orchestrator_pipeline(
        orchestrators.get_billing_overview_orchestrator
    )
    start_trial_pipeline = orchestrator_pipeline(orchestrators.start_trial_orchestrator)
    change_plan_pipeline = orchestrator_pipeline(orchestrators.change_plan_orchestrator)
    cancel_subscription_pipeline = orchestrator_pipeline(
        orchestrators.cancel_subscription_orchestrator
    )
    start_checkout_pipeline = orchestrator_pipeline(
        orchestrators.start_checkout_orchestrator
    )
    process_payment_webhook_pipeline = orchestrator_pipeline(
        orchestrators.process_payment_webhook_orchestrator
    )

    # --- Platform admin.
    list_clients_pipeline = orchestrator_pipeline(
        orchestrators.list_clients_orchestrator
    )
    get_client_health_pipeline = orchestrator_pipeline(
        orchestrators.get_client_health_orchestrator
    )
    open_client_cabinet_pipeline = orchestrator_pipeline(
        orchestrators.open_client_cabinet_orchestrator
    )

    # --- Periodic jobs of the background worker.
    end_trials_pipeline = orchestrator_pipeline(orchestrators.end_trials_orchestrator)
    enforce_grace_periods_pipeline = orchestrator_pipeline(
        orchestrators.enforce_grace_periods_orchestrator
    )
    check_package_usage_pipeline = orchestrator_pipeline(
        orchestrators.check_package_usage_orchestrator
    )
    invoice_usage_overage_pipeline = orchestrator_pipeline(
        orchestrators.invoice_usage_overage_orchestrator
    )
    send_booking_reminders_pipeline = orchestrator_pipeline(
        orchestrators.send_booking_reminders_orchestrator
    )
    flush_llm_traces_pipeline = orchestrator_pipeline(
        orchestrators.flush_llm_traces_orchestrator
    )

from dependency_injector import containers
from dependency_injector.providers import Factory, Singleton

from app.containers.container_edges import composed_container_edge
from app.containers.orchestrators.orchestrators_container import (
    OrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline
from app.containers.use_cases.use_cases_container import UseCasesContainer
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

    orchestrators: OrchestratorsContainer = composed_container_edge(  # type: ignore[assignment]
        OrchestratorsContainer
    )
    use_cases: UseCasesContainer = composed_container_edge(UseCasesContainer)  # type: ignore[assignment]

    # --- Customer messages of every channel. Singleton: its per-customer
    # locks must be shared by every channel of the process.
    customer_message_pipeline: Singleton[CustomerMessagePipelineContract] = Singleton(
        CustomerMessagePipeline,
        turn_orchestrator=orchestrators.conversations.conversation_turn_orchestrator,
    )
    owner_test_chat_pipeline: Factory[
        PipelineContract[OwnerTestChatCommand, AssistantReply]
    ] = Factory(
        OwnerTestChatPipeline,
        prepare_test_message=orchestrators.conversations.owner_test_chat_orchestrator,
        turn_orchestrator=orchestrators.conversations.conversation_turn_orchestrator,
    )
    assemble_assistant_version_pipeline: Factory[
        PipelineContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        AssembleAssistantVersionPipeline,
        assemble_assistant_version=orchestrators.assistants.assemble_assistant_version_orchestrator,
        run_autotests=orchestrators.assistants.queue_autotest_run_orchestrator,
        get_assistant_version=orchestrators.assistants.get_assistant_version_orchestrator,
    )

    # --- Messaging webhooks and the website widget.
    telegram_webhook_orchestrator: Factory[
        OrchestratorContract[TelegramWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[TelegramWebhookRequest],
        receive_webhook=use_cases.channels.receive_telegram_webhook_use_case,
        customer_message_pipeline=customer_message_pipeline,
        deliver_reply=use_cases.channels.deliver_channel_reply_use_case,
    )
    meta_webhook_orchestrator: Factory[
        OrchestratorContract[MetaWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[MetaWebhookRequest],
        receive_webhook=use_cases.channels.receive_meta_webhook_use_case,
        customer_message_pipeline=customer_message_pipeline,
        deliver_reply=use_cases.channels.deliver_channel_reply_use_case,
    )
    widget_message_orchestrator: Factory[
        OrchestratorContract[WidgetMessageCommand, WidgetReplyView]
    ] = Factory(
        WidgetMessageOrchestrator,
        accept_widget_message=use_cases.channels.accept_widget_message_use_case,
        customer_message_pipeline=customer_message_pipeline,
        build_widget_reply=use_cases.channels.build_widget_reply_use_case,
    )
    telegram_webhook_pipeline = orchestrator_pipeline(telegram_webhook_orchestrator)
    meta_webhook_pipeline = orchestrator_pipeline(meta_webhook_orchestrator)
    widget_message_pipeline = orchestrator_pipeline(widget_message_orchestrator)

    # --- Dedicated orchestrators.
    call_forwarding_instructions_pipeline = orchestrator_pipeline(
        orchestrators.accounts.call_forwarding_instructions_orchestrator
    )
    run_autotests_pipeline = orchestrator_pipeline(
        orchestrators.assistants.queue_autotest_run_orchestrator
    )
    run_queued_autotests_pipeline = orchestrator_pipeline(
        orchestrators.assistants.run_queued_autotests_orchestrator
    )
    voice_tool_webhook_pipeline = orchestrator_pipeline(
        orchestrators.conversations.voice_tool_webhook_orchestrator
    )
    post_call_webhook_pipeline = orchestrator_pipeline(
        orchestrators.conversations.post_call_webhook_orchestrator
    )
    purge_expired_recordings_pipeline = orchestrator_pipeline(
        orchestrators.compliance.purge_expired_recordings_job_orchestrator
    )

    # --- One orchestrator per endpoint or job.

    # --- Catalog.
    list_countries_pipeline = orchestrator_pipeline(
        orchestrators.accounts.list_countries_orchestrator
    )
    get_country_profile_pipeline = orchestrator_pipeline(
        orchestrators.accounts.get_country_profile_orchestrator
    )
    list_languages_pipeline = orchestrator_pipeline(
        orchestrators.accounts.list_languages_orchestrator
    )
    quote_plans_pipeline = orchestrator_pipeline(
        orchestrators.accounts.quote_plans_orchestrator
    )
    parse_phone_number_pipeline = orchestrator_pipeline(
        orchestrators.accounts.parse_phone_number_orchestrator
    )

    # --- Sign-in and the current user.
    authenticate_user_pipeline = orchestrator_pipeline(
        orchestrators.accounts.authenticate_user_orchestrator
    )
    start_otp_login_pipeline = orchestrator_pipeline(
        orchestrators.accounts.start_otp_login_orchestrator
    )
    get_login_options_pipeline = orchestrator_pipeline(
        orchestrators.accounts.get_login_options_orchestrator
    )
    verify_otp_login_pipeline = orchestrator_pipeline(
        orchestrators.accounts.verify_otp_login_orchestrator
    )
    logout_pipeline = orchestrator_pipeline(orchestrators.accounts.logout_orchestrator)
    get_current_user_pipeline = orchestrator_pipeline(
        orchestrators.accounts.get_current_user_orchestrator
    )
    update_current_user_pipeline = orchestrator_pipeline(
        orchestrators.accounts.update_current_user_orchestrator
    )

    # --- Businesses and teams.
    authorize_business_access_pipeline = orchestrator_pipeline(
        orchestrators.accounts.authorize_business_access_orchestrator
    )
    create_business_pipeline = orchestrator_pipeline(
        orchestrators.accounts.create_business_orchestrator
    )
    list_my_businesses_pipeline = orchestrator_pipeline(
        orchestrators.accounts.list_my_businesses_orchestrator
    )
    get_business_pipeline = orchestrator_pipeline(
        orchestrators.accounts.get_business_orchestrator
    )
    update_business_settings_pipeline = orchestrator_pipeline(
        orchestrators.accounts.update_business_settings_orchestrator
    )
    invite_staff_pipeline = orchestrator_pipeline(
        orchestrators.accounts.invite_staff_orchestrator
    )
    remove_member_pipeline = orchestrator_pipeline(
        orchestrators.accounts.remove_member_orchestrator
    )
    change_member_role_pipeline = orchestrator_pipeline(
        orchestrators.accounts.change_member_role_orchestrator
    )

    # --- Compliance.
    get_dpa_status_pipeline = orchestrator_pipeline(
        orchestrators.compliance.get_dpa_status_orchestrator
    )
    accept_dpa_pipeline = orchestrator_pipeline(
        orchestrators.compliance.accept_dpa_orchestrator
    )
    list_audit_log_pipeline = orchestrator_pipeline(
        orchestrators.compliance.list_audit_log_orchestrator
    )
    export_contact_data_pipeline = orchestrator_pipeline(
        orchestrators.compliance.export_contact_data_orchestrator
    )
    delete_contact_data_pipeline = orchestrator_pipeline(
        orchestrators.compliance.delete_contact_data_orchestrator
    )
    get_dpa_document_pipeline = orchestrator_pipeline(
        orchestrators.compliance.get_dpa_document_orchestrator
    )
    list_contacts_pipeline = orchestrator_pipeline(
        orchestrators.compliance.list_contacts_orchestrator
    )
    get_contact_pipeline = orchestrator_pipeline(
        orchestrators.compliance.get_contact_orchestrator
    )

    # --- Niche templates and the profile wizard.
    list_niche_templates_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.list_niche_templates_orchestrator
    )
    get_niche_template_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.get_niche_template_orchestrator
    )
    get_profile_wizard_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.get_profile_wizard_orchestrator
    )
    get_business_profile_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.get_business_profile_orchestrator
    )
    save_profile_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.save_profile_orchestrator
    )
    save_profile_step_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.save_profile_step_orchestrator
    )
    compute_profile_gaps_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.compute_profile_gaps_orchestrator
    )

    # --- Knowledge base.
    list_knowledge_items_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.list_knowledge_items_orchestrator
    )
    create_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.create_knowledge_item_orchestrator
    )
    get_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.get_knowledge_item_orchestrator
    )
    update_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.update_knowledge_item_orchestrator
    )
    delete_knowledge_item_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.delete_knowledge_item_orchestrator
    )
    search_knowledge_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.search_knowledge_orchestrator
    )

    # --- Resources and schedule exceptions.
    list_resources_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.list_resources_orchestrator
    )
    create_resource_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.create_resource_orchestrator
    )
    update_resource_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.update_resource_orchestrator
    )
    list_schedule_exceptions_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.list_schedule_exceptions_orchestrator
    )
    create_schedule_exception_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.create_schedule_exception_orchestrator
    )
    delete_schedule_exception_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.delete_schedule_exception_orchestrator
    )

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_pipeline = orchestrator_pipeline(
        orchestrators.operations.check_availability_orchestrator
    )
    list_bookings_pipeline = orchestrator_pipeline(
        orchestrators.operations.list_bookings_orchestrator
    )
    create_manual_booking_pipeline = orchestrator_pipeline(
        orchestrators.operations.create_manual_booking_orchestrator
    )
    cancel_booking_pipeline = orchestrator_pipeline(
        orchestrators.operations.cancel_booking_orchestrator
    )
    reschedule_booking_pipeline = orchestrator_pipeline(
        orchestrators.operations.reschedule_booking_orchestrator
    )
    update_booking_pipeline = orchestrator_pipeline(
        orchestrators.operations.update_booking_orchestrator
    )
    list_leads_pipeline = orchestrator_pipeline(
        orchestrators.operations.list_leads_orchestrator
    )
    update_lead_status_pipeline = orchestrator_pipeline(
        orchestrators.operations.update_lead_status_orchestrator
    )
    list_handoffs_pipeline = orchestrator_pipeline(
        orchestrators.operations.list_handoffs_orchestrator
    )
    resolve_handoff_pipeline = orchestrator_pipeline(
        orchestrators.operations.resolve_handoff_orchestrator
    )
    list_unanswered_questions_pipeline = orchestrator_pipeline(
        orchestrators.operations.list_unanswered_questions_orchestrator
    )
    answer_unanswered_question_pipeline = orchestrator_pipeline(
        orchestrators.operations.answer_unanswered_question_orchestrator
    )
    get_dashboard_stats_pipeline = orchestrator_pipeline(
        orchestrators.operations.get_dashboard_stats_orchestrator
    )
    start_google_calendar_connection_pipeline = orchestrator_pipeline(
        orchestrators.operations.start_google_calendar_connection_orchestrator
    )
    complete_google_calendar_connection_pipeline = orchestrator_pipeline(
        orchestrators.operations.complete_google_calendar_connection_orchestrator
    )
    disconnect_google_calendar_pipeline = orchestrator_pipeline(
        orchestrators.operations.disconnect_google_calendar_orchestrator
    )
    get_google_calendar_connection_pipeline = orchestrator_pipeline(
        orchestrators.operations.get_google_calendar_connection_orchestrator
    )

    # --- Conversation feed and menu import.
    list_conversations_pipeline = orchestrator_pipeline(
        orchestrators.conversations.list_conversations_orchestrator
    )
    get_conversation_pipeline = orchestrator_pipeline(
        orchestrators.conversations.get_conversation_orchestrator
    )
    rate_conversation_pipeline = orchestrator_pipeline(
        orchestrators.conversations.rate_conversation_orchestrator
    )
    send_staff_message_pipeline = orchestrator_pipeline(
        orchestrators.conversations.send_staff_message_orchestrator
    )
    get_call_recording_pipeline = orchestrator_pipeline(
        orchestrators.conversations.get_call_recording_orchestrator
    )
    import_menu_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.import_menu_orchestrator
    )
    confirm_imported_items_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.confirm_imported_items_orchestrator
    )
    discard_import_batch_pipeline = orchestrator_pipeline(
        orchestrators.knowledge.discard_import_batch_orchestrator
    )

    # --- Assistant versions and autotests.
    list_assistant_versions_pipeline = orchestrator_pipeline(
        orchestrators.assistants.list_assistant_versions_orchestrator
    )
    get_assistant_version_pipeline = orchestrator_pipeline(
        orchestrators.assistants.get_assistant_version_orchestrator
    )
    get_autotest_run_pipeline = orchestrator_pipeline(
        orchestrators.assistants.get_autotest_run_orchestrator
    )
    get_go_live_readiness_pipeline = orchestrator_pipeline(
        orchestrators.assistants.get_go_live_readiness_orchestrator
    )
    publish_assistant_version_pipeline = orchestrator_pipeline(
        orchestrators.assistants.publish_assistant_version_orchestrator
    )
    rollback_assistant_version_pipeline = orchestrator_pipeline(
        orchestrators.assistants.rollback_assistant_version_orchestrator
    )

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_pipeline = orchestrator_pipeline(
        orchestrators.channels.verify_meta_webhook_orchestrator
    )
    handle_platform_bot_update_pipeline = orchestrator_pipeline(
        orchestrators.channels.handle_platform_bot_update_orchestrator
    )
    get_widget_config_pipeline = orchestrator_pipeline(
        orchestrators.channels.get_widget_config_orchestrator
    )
    get_widget_messages_pipeline = orchestrator_pipeline(
        orchestrators.channels.get_widget_messages_orchestrator
    )
    list_channels_pipeline = orchestrator_pipeline(
        orchestrators.channels.list_channels_orchestrator
    )
    connect_channel_pipeline = orchestrator_pipeline(
        orchestrators.channels.connect_channel_orchestrator
    )
    disable_channel_pipeline = orchestrator_pipeline(
        orchestrators.channels.disable_channel_orchestrator
    )
    set_whatsapp_staff_template_pipeline = orchestrator_pipeline(
        orchestrators.channels.set_whatsapp_staff_template_orchestrator
    )
    get_widget_snippet_pipeline = orchestrator_pipeline(
        orchestrators.channels.get_widget_snippet_orchestrator
    )
    create_telegram_link_pipeline = orchestrator_pipeline(
        orchestrators.channels.create_telegram_link_orchestrator
    )
    configure_platform_bot_webhook_pipeline = orchestrator_pipeline(
        orchestrators.channels.configure_platform_bot_webhook_orchestrator
    )

    # --- Voice webhooks.
    start_voice_call_pipeline = orchestrator_pipeline(
        orchestrators.conversations.start_voice_call_orchestrator
    )

    # --- Billing and payments.
    get_billing_overview_pipeline = orchestrator_pipeline(
        orchestrators.billing.get_billing_overview_orchestrator
    )
    start_trial_pipeline = orchestrator_pipeline(
        orchestrators.billing.start_trial_orchestrator
    )
    change_plan_pipeline = orchestrator_pipeline(
        orchestrators.billing.change_plan_orchestrator
    )
    cancel_subscription_pipeline = orchestrator_pipeline(
        orchestrators.billing.cancel_subscription_orchestrator
    )
    start_checkout_pipeline = orchestrator_pipeline(
        orchestrators.billing.start_checkout_orchestrator
    )
    subscribe_pipeline = orchestrator_pipeline(
        orchestrators.billing.subscribe_orchestrator
    )
    process_payment_webhook_pipeline = orchestrator_pipeline(
        orchestrators.billing.process_payment_webhook_orchestrator
    )

    # --- Platform admin.
    list_clients_pipeline = orchestrator_pipeline(
        orchestrators.platform.list_clients_orchestrator
    )
    get_client_health_pipeline = orchestrator_pipeline(
        orchestrators.platform.get_client_health_orchestrator
    )
    open_client_cabinet_pipeline = orchestrator_pipeline(
        orchestrators.platform.open_client_cabinet_orchestrator
    )

    # --- Periodic jobs of the background worker.
    end_trials_pipeline = orchestrator_pipeline(
        orchestrators.billing.end_trials_orchestrator
    )
    enforce_grace_periods_pipeline = orchestrator_pipeline(
        orchestrators.billing.enforce_grace_periods_orchestrator
    )
    check_package_usage_pipeline = orchestrator_pipeline(
        orchestrators.billing.check_package_usage_orchestrator
    )
    invoice_usage_overage_pipeline = orchestrator_pipeline(
        orchestrators.billing.invoice_usage_overage_orchestrator
    )
    send_booking_reminders_pipeline = orchestrator_pipeline(
        orchestrators.operations.send_booking_reminders_orchestrator
    )
    flush_llm_traces_pipeline = orchestrator_pipeline(
        orchestrators.platform.flush_llm_traces_orchestrator
    )

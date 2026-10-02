from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.provider_chains import use_case_orchestrator
from app.containers.repositories import RepositoriesContainer
from app.containers.use_cases.use_cases_container import UseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.conversation_flow import (
    ConversationTurnOrchestratorContract,
    VoiceToolCallOrchestratorContract,
)
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.assistants.queue_autotest_run_orchestrator import (
    QueueAutotestRunOrchestrator,
)
from app.orchestrators.assistants.run_autotests_orchestrator import (
    RunAutotestsOrchestrator,
)
from app.orchestrators.assistants.run_queued_autotests_orchestrator import (
    RunQueuedAutotestsOrchestrator,
)
from app.orchestrators.billing.subscribe_orchestrator import SubscribeOrchestrator
from app.orchestrators.channels.post_call_webhook_orchestrator import (
    PostCallWebhookOrchestrator,
)
from app.orchestrators.channels.voice_tool_webhook_orchestrator import (
    VoiceToolWebhookOrchestrator,
)
from app.orchestrators.compliance.purge_expired_recordings_job_orchestrator import (
    PurgeExpiredRecordingsJobOrchestrator,
)
from app.orchestrators.conversations.conversation_turn_orchestrator import (
    ConversationTurnOrchestrator,
)
from app.orchestrators.conversations.owner_test_chat_orchestrator import (
    OwnerTestChatOrchestrator,
)
from app.orchestrators.conversations.voice_tool_call_orchestrator import (
    VoiceToolCallOrchestrator,
)
from app.orchestrators.localization.call_forwarding_instructions_orchestrator import (
    CallForwardingInstructionsOrchestrator,
)
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants import (
    AutotestRunView,
    AutotestScenarioRun,
    RunAutotestsCommand,
)
from app.schemas.dto.billing_cabinet import CheckoutSessionView, SubscribeCommand
from app.schemas.dto.catalog import (
    CallForwardingInstructions,
    CallForwardingInstructionsRequest,
)
from app.schemas.dto.conversation_feed import OwnerTestChatCommand
from app.schemas.dto.conversations import InboundMessage, VoiceToolCallResult
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.dto.voice_webhooks import (
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
    VoiceToolWebhookRequest,
)
from app.use_cases.autotests.run_autotest_scenario_use_case import (
    RunAutotestScenarioUseCase,
)


class OrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators: the generic one around each single-use-case endpoint and
    the dedicated ones that coordinate several use cases.

    The autotest scenario runner is a use case of the assembly module, but it
    drives the conversation turn orchestrator, so it is wired here (the
    use cases container cannot depend on orchestrators).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    use_cases: UseCasesContainer = composed_container_edge(UseCasesContainer)  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Conversation engine: one customer message, one voice tool call.
    conversation_turn_orchestrator: Factory[ConversationTurnOrchestratorContract] = (
        Factory(
            ConversationTurnOrchestrator,
            prepare_turn=use_cases.conversations.prepare_conversation_turn_use_case,
            generate_reply=use_cases.conversations.generate_assistant_reply_use_case,
            handoff_to_human=use_cases.follow_ups.handoff_to_human_use_case,
            record_reply=use_cases.conversations.record_assistant_reply_use_case,
            localized_text_resolver=utilities.localized_text_resolver,
            storage_scope=utilities.storage_scope,
        )
    )
    voice_tool_call_orchestrator: Factory[VoiceToolCallOrchestratorContract] = Factory(
        VoiceToolCallOrchestrator,
        open_voice_conversation=use_cases.conversations.open_voice_conversation_use_case,
        run_assistant_tool=use_cases.conversations.run_assistant_tool_use_case,
        record_voice_tool_call=use_cases.conversations.record_voice_tool_call_use_case,
        storage_scope=utilities.storage_scope,
    )
    owner_test_chat_orchestrator: Factory[
        OrchestratorContract[OwnerTestChatCommand, InboundMessage]
    ] = Factory(
        OwnerTestChatOrchestrator,
        authorize_business_access=use_cases.accounts.authorize_business_access_use_case,
        resolve_test_chat_version=use_cases.conversation_feed.resolve_test_chat_version_use_case,
    )

    # --- Autotests: AI customer and judge share the traced LLM adapter.
    run_autotest_scenario_use_case: Factory[
        UseCaseContract[AutotestScenarioRun, AutotestScenarioResult]
    ] = Factory(
        RunAutotestScenarioUseCase,
        conversation_turn_orchestrator=conversation_turn_orchestrator,
        customer_llm_adapter=adapters.llm_adapter,
        judge_llm_adapter=adapters.llm_adapter,
        message_repo=repositories.message_repo,
        app_settings=config.app_settings,
    )
    run_autotests_orchestrator: Factory[
        OrchestratorContract[RunAutotestsCommand, AutotestRunView]
    ] = Factory(
        RunAutotestsOrchestrator,
        start_autotest_run=use_cases.autotests.start_autotest_run_use_case,
        run_autotest_scenario=run_autotest_scenario_use_case,
        finish_autotest_run=use_cases.autotests.finish_autotest_run_use_case,
    )
    # The HTTP routes start a run and leave playing it to the worker.
    queue_autotest_run_orchestrator: Factory[
        OrchestratorContract[RunAutotestsCommand, AutotestRunView]
    ] = Factory(
        QueueAutotestRunOrchestrator,
        start_autotest_run=use_cases.autotests.start_autotest_run_use_case,
        enqueue_autotest_run=use_cases.autotests.enqueue_autotest_run_use_case,
    )
    run_queued_autotests_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        RunQueuedAutotestsOrchestrator,
        resume_autotest_run=use_cases.autotests.resume_autotest_run_use_case,
        run_autotest_scenario=run_autotest_scenario_use_case,
        finish_autotest_run=use_cases.autotests.finish_autotest_run_use_case,
        abandon_autotest_run=use_cases.autotests.abandon_autotest_run_use_case,
        record_autotest_progress=use_cases.autotests.record_autotest_progress_use_case,
    )

    # --- Call forwarding instructions (access check, then the instructions).
    call_forwarding_instructions_orchestrator: Factory[
        OrchestratorContract[
            CallForwardingInstructionsRequest,
            CallForwardingInstructions,
        ]
    ] = Factory(
        CallForwardingInstructionsOrchestrator,
        authorize_business_access_use_case=use_cases.accounts.authorize_business_access_use_case,
        build_call_forwarding_instructions_use_case=(
            use_cases.catalog.build_call_forwarding_instructions_use_case
        ),
    )

    # --- Voice webhooks.
    voice_tool_webhook_orchestrator: Factory[
        OrchestratorContract[VoiceToolWebhookRequest, VoiceToolCallResult]
    ] = Factory(
        VoiceToolWebhookOrchestrator,
        authenticate_voice_tool_call=use_cases.voice.authenticate_voice_tool_call_use_case,
        voice_tool_call=voice_tool_call_orchestrator,
    )
    post_call_webhook_orchestrator: Factory[
        OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
    ] = Factory(
        PostCallWebhookOrchestrator,
        authenticate_post_call=use_cases.voice.authenticate_post_call_use_case,
        record_finished_call=use_cases.voice.record_finished_call_use_case,
        send_call_confirmation=use_cases.voice.send_call_confirmation_use_case,
    )

    # --- Retention purge as a periodic job.
    purge_expired_recordings_job_orchestrator: Factory[
        OrchestratorContract[JobTick, JobReport]
    ] = Factory(
        PurgeExpiredRecordingsJobOrchestrator,
        purge_expired_recordings=use_cases.compliance.purge_expired_recordings_use_case,
    )

    # --- Subscribing with payment now: open, switch plan, checkout.
    subscribe_orchestrator: Factory[
        OrchestratorContract[SubscribeCommand, CheckoutSessionView]
    ] = Factory(
        SubscribeOrchestrator,
        open_subscription=use_cases.billing.open_subscription_use_case,
        change_plan=use_cases.billing.change_plan_use_case,
        start_checkout=use_cases.billing.start_checkout_use_case,
    )

    # --- One use case per endpoint or job (typed through the use case).

    # --- Catalog.
    list_countries_orchestrator = use_case_orchestrator(
        use_cases.catalog.list_countries_use_case
    )
    get_country_profile_orchestrator = use_case_orchestrator(
        use_cases.catalog.get_country_profile_use_case
    )
    list_languages_orchestrator = use_case_orchestrator(
        use_cases.catalog.list_languages_use_case
    )
    quote_plans_orchestrator = use_case_orchestrator(
        use_cases.catalog.quote_plans_use_case
    )
    parse_phone_number_orchestrator = use_case_orchestrator(
        use_cases.catalog.parse_phone_number_use_case
    )

    # --- Sign-in and the current user.
    authenticate_user_orchestrator = use_case_orchestrator(
        use_cases.accounts.authenticate_user_use_case
    )
    start_otp_login_orchestrator = use_case_orchestrator(
        use_cases.accounts.start_otp_login_use_case
    )
    get_login_options_orchestrator = use_case_orchestrator(
        use_cases.accounts.get_login_options_use_case
    )
    verify_otp_login_orchestrator = use_case_orchestrator(
        use_cases.accounts.verify_otp_login_use_case
    )
    logout_orchestrator = use_case_orchestrator(use_cases.accounts.logout_use_case)
    get_current_user_orchestrator = use_case_orchestrator(
        use_cases.accounts.get_current_user_use_case
    )
    update_current_user_orchestrator = use_case_orchestrator(
        use_cases.accounts.update_current_user_use_case
    )

    # --- Businesses and teams.
    authorize_business_access_orchestrator = use_case_orchestrator(
        use_cases.accounts.authorize_business_access_use_case
    )
    create_business_orchestrator = use_case_orchestrator(
        use_cases.accounts.create_business_use_case
    )
    list_my_businesses_orchestrator = use_case_orchestrator(
        use_cases.accounts.list_my_businesses_use_case
    )
    get_business_orchestrator = use_case_orchestrator(
        use_cases.accounts.get_business_use_case
    )
    update_business_settings_orchestrator = use_case_orchestrator(
        use_cases.assistants.update_business_settings_use_case
    )
    invite_staff_orchestrator = use_case_orchestrator(
        use_cases.accounts.invite_staff_use_case
    )
    remove_member_orchestrator = use_case_orchestrator(
        use_cases.accounts.remove_member_use_case
    )
    change_member_role_orchestrator = use_case_orchestrator(
        use_cases.accounts.change_member_role_use_case
    )

    # --- Compliance.
    get_dpa_status_orchestrator = use_case_orchestrator(
        use_cases.compliance.get_dpa_status_use_case
    )
    accept_dpa_orchestrator = use_case_orchestrator(
        use_cases.compliance.accept_dpa_use_case
    )
    list_audit_log_orchestrator = use_case_orchestrator(
        use_cases.compliance.list_audit_log_use_case
    )
    export_contact_data_orchestrator = use_case_orchestrator(
        use_cases.compliance.export_contact_data_use_case
    )
    delete_contact_data_orchestrator = use_case_orchestrator(
        use_cases.compliance.delete_contact_data_use_case
    )
    get_dpa_document_orchestrator = use_case_orchestrator(
        use_cases.compliance.get_dpa_document_use_case
    )
    list_contacts_orchestrator = use_case_orchestrator(
        use_cases.compliance.list_contacts_use_case
    )
    get_contact_orchestrator = use_case_orchestrator(
        use_cases.compliance.get_contact_use_case
    )

    # --- Niche templates and the profile wizard.
    list_niche_templates_orchestrator = use_case_orchestrator(
        use_cases.knowledge.list_niche_templates_use_case
    )
    get_niche_template_orchestrator = use_case_orchestrator(
        use_cases.knowledge.get_niche_template_use_case
    )
    get_profile_wizard_orchestrator = use_case_orchestrator(
        use_cases.knowledge.get_profile_wizard_use_case
    )
    get_business_profile_orchestrator = use_case_orchestrator(
        use_cases.knowledge.get_business_profile_use_case
    )
    save_profile_orchestrator = use_case_orchestrator(
        use_cases.knowledge.save_profile_use_case
    )
    save_profile_step_orchestrator = use_case_orchestrator(
        use_cases.knowledge.save_profile_step_use_case
    )
    compute_profile_gaps_orchestrator = use_case_orchestrator(
        use_cases.knowledge.compute_profile_gaps_use_case
    )

    # --- Knowledge base.
    list_knowledge_items_orchestrator = use_case_orchestrator(
        use_cases.knowledge.list_knowledge_items_use_case
    )
    create_knowledge_item_orchestrator = use_case_orchestrator(
        use_cases.knowledge.create_knowledge_item_use_case
    )
    get_knowledge_item_orchestrator = use_case_orchestrator(
        use_cases.knowledge.get_knowledge_item_use_case
    )
    update_knowledge_item_orchestrator = use_case_orchestrator(
        use_cases.knowledge.update_knowledge_item_use_case
    )
    delete_knowledge_item_orchestrator = use_case_orchestrator(
        use_cases.knowledge.delete_knowledge_item_use_case
    )
    search_knowledge_orchestrator = use_case_orchestrator(
        use_cases.knowledge.search_knowledge_use_case
    )

    # --- Resources and schedule exceptions.
    list_resources_orchestrator = use_case_orchestrator(
        use_cases.scheduling.list_resources_use_case
    )
    create_resource_orchestrator = use_case_orchestrator(
        use_cases.scheduling.create_resource_use_case
    )
    update_resource_orchestrator = use_case_orchestrator(
        use_cases.scheduling.update_resource_use_case
    )
    list_schedule_exceptions_orchestrator = use_case_orchestrator(
        use_cases.scheduling.list_schedule_exceptions_use_case
    )
    create_schedule_exception_orchestrator = use_case_orchestrator(
        use_cases.scheduling.create_schedule_exception_use_case
    )
    delete_schedule_exception_orchestrator = use_case_orchestrator(
        use_cases.scheduling.delete_schedule_exception_use_case
    )

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_orchestrator = use_case_orchestrator(
        use_cases.bookings.check_availability_use_case
    )
    list_bookings_orchestrator = use_case_orchestrator(
        use_cases.bookings.list_bookings_use_case
    )
    create_manual_booking_orchestrator = use_case_orchestrator(
        use_cases.bookings.create_manual_booking_use_case
    )
    cancel_booking_orchestrator = use_case_orchestrator(
        use_cases.bookings.cancel_booking_use_case
    )
    reschedule_booking_orchestrator = use_case_orchestrator(
        use_cases.bookings.reschedule_booking_use_case
    )
    update_booking_orchestrator = use_case_orchestrator(
        use_cases.bookings.update_booking_use_case
    )
    list_leads_orchestrator = use_case_orchestrator(
        use_cases.follow_ups.list_leads_use_case
    )
    update_lead_status_orchestrator = use_case_orchestrator(
        use_cases.follow_ups.update_lead_status_use_case
    )
    list_handoffs_orchestrator = use_case_orchestrator(
        use_cases.follow_ups.list_handoffs_use_case
    )
    resolve_handoff_orchestrator = use_case_orchestrator(
        use_cases.follow_ups.resolve_handoff_use_case
    )
    list_unanswered_questions_orchestrator = use_case_orchestrator(
        use_cases.follow_ups.list_unanswered_questions_use_case
    )
    answer_unanswered_question_orchestrator = use_case_orchestrator(
        use_cases.follow_ups.answer_unanswered_question_use_case
    )
    get_dashboard_stats_orchestrator = use_case_orchestrator(
        use_cases.follow_ups.get_dashboard_stats_use_case
    )
    start_google_calendar_connection_orchestrator = use_case_orchestrator(
        use_cases.scheduling.start_google_calendar_connection_use_case
    )
    complete_google_calendar_connection_orchestrator = use_case_orchestrator(
        use_cases.scheduling.complete_google_calendar_connection_use_case
    )
    disconnect_google_calendar_orchestrator = use_case_orchestrator(
        use_cases.scheduling.disconnect_google_calendar_use_case
    )
    get_google_calendar_connection_orchestrator = use_case_orchestrator(
        use_cases.scheduling.get_google_calendar_connection_use_case
    )

    # --- Conversation feed and menu import.
    list_conversations_orchestrator = use_case_orchestrator(
        use_cases.conversation_feed.list_conversations_use_case
    )
    get_conversation_orchestrator = use_case_orchestrator(
        use_cases.conversation_feed.get_conversation_use_case
    )
    rate_conversation_orchestrator = use_case_orchestrator(
        use_cases.conversation_feed.rate_conversation_use_case
    )
    send_staff_message_orchestrator = use_case_orchestrator(
        use_cases.conversation_feed.send_staff_message_use_case
    )
    get_call_recording_orchestrator = use_case_orchestrator(
        use_cases.conversation_feed.get_call_recording_use_case
    )
    import_menu_orchestrator = use_case_orchestrator(
        use_cases.menu_import.import_menu_use_case
    )
    confirm_imported_items_orchestrator = use_case_orchestrator(
        use_cases.menu_import.confirm_imported_items_use_case
    )
    discard_import_batch_orchestrator = use_case_orchestrator(
        use_cases.menu_import.discard_import_batch_use_case
    )

    # --- Assistant versions and autotests.
    assemble_assistant_version_orchestrator = use_case_orchestrator(
        use_cases.assistants.assemble_assistant_version_use_case
    )
    list_assistant_versions_orchestrator = use_case_orchestrator(
        use_cases.assistants.list_assistant_versions_use_case
    )
    get_assistant_version_orchestrator = use_case_orchestrator(
        use_cases.assistants.get_assistant_version_use_case
    )
    get_autotest_run_orchestrator = use_case_orchestrator(
        use_cases.autotests.get_autotest_run_use_case
    )
    get_go_live_readiness_orchestrator = use_case_orchestrator(
        use_cases.assistants.get_go_live_readiness_use_case
    )
    publish_assistant_version_orchestrator = use_case_orchestrator(
        use_cases.assistants.publish_assistant_version_use_case
    )
    rollback_assistant_version_orchestrator = use_case_orchestrator(
        use_cases.assistants.rollback_assistant_version_use_case
    )

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_orchestrator = use_case_orchestrator(
        use_cases.channels.verify_meta_webhook_use_case
    )
    handle_platform_bot_update_orchestrator = use_case_orchestrator(
        use_cases.channels.handle_platform_bot_update_use_case
    )
    get_widget_config_orchestrator = use_case_orchestrator(
        use_cases.channels.get_widget_config_use_case
    )
    get_widget_messages_orchestrator = use_case_orchestrator(
        use_cases.channels.get_widget_messages_use_case
    )
    list_channels_orchestrator = use_case_orchestrator(
        use_cases.channels.list_channels_use_case
    )
    connect_channel_orchestrator = use_case_orchestrator(
        use_cases.channels.connect_channel_use_case
    )
    disable_channel_orchestrator = use_case_orchestrator(
        use_cases.channels.disable_channel_use_case
    )
    set_whatsapp_staff_template_orchestrator = use_case_orchestrator(
        use_cases.channels.set_whatsapp_staff_template_use_case
    )
    get_widget_snippet_orchestrator = use_case_orchestrator(
        use_cases.channels.get_widget_snippet_use_case
    )
    create_telegram_link_orchestrator = use_case_orchestrator(
        use_cases.channels.create_telegram_link_use_case
    )
    configure_platform_bot_webhook_orchestrator = use_case_orchestrator(
        use_cases.channels.configure_platform_bot_webhook_use_case
    )

    # --- Voice webhooks.
    start_voice_call_orchestrator = use_case_orchestrator(
        use_cases.voice.start_voice_call_use_case
    )

    # --- Billing and payments.
    get_billing_overview_orchestrator = use_case_orchestrator(
        use_cases.billing.get_billing_overview_use_case
    )
    start_trial_orchestrator = use_case_orchestrator(
        use_cases.billing.start_trial_use_case
    )
    change_plan_orchestrator = use_case_orchestrator(
        use_cases.billing.change_plan_use_case
    )
    cancel_subscription_orchestrator = use_case_orchestrator(
        use_cases.billing.cancel_subscription_use_case
    )
    start_checkout_orchestrator = use_case_orchestrator(
        use_cases.billing.start_checkout_use_case
    )
    process_payment_webhook_orchestrator = use_case_orchestrator(
        use_cases.billing.process_payment_webhook_use_case
    )

    # --- Platform admin.
    list_clients_orchestrator = use_case_orchestrator(
        use_cases.platform.list_clients_use_case
    )
    get_client_health_orchestrator = use_case_orchestrator(
        use_cases.platform.get_client_health_use_case
    )
    open_client_cabinet_orchestrator = use_case_orchestrator(
        use_cases.platform.open_client_cabinet_use_case
    )

    # --- Periodic jobs of the background worker.
    end_trials_orchestrator = use_case_orchestrator(
        use_cases.billing.end_trials_use_case
    )
    enforce_grace_periods_orchestrator = use_case_orchestrator(
        use_cases.billing.enforce_grace_periods_use_case
    )
    check_package_usage_orchestrator = use_case_orchestrator(
        use_cases.billing.check_package_usage_use_case
    )
    invoice_usage_overage_orchestrator = use_case_orchestrator(
        use_cases.billing.invoice_usage_overage_use_case
    )
    send_booking_reminders_orchestrator = use_case_orchestrator(
        use_cases.bookings.send_booking_reminders_use_case
    )
    flush_llm_traces_orchestrator = use_case_orchestrator(
        use_cases.platform.flush_llm_traces_use_case
    )

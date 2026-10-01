from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines import PipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class OperatorsContainer(containers.DeclarativeContainer):
    """
    One operator per HTTP endpoint and per worker job. Each runs its
    pipeline synchronously, inside the storage scope of the business its
    input names (row-level security on Postgres); input and output types
    come from the use case or orchestrator at the bottom of the chain.
    """

    pipelines: PipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    # --- Dedicated pipelines and orchestrators.
    owner_test_chat_operator = pipeline_operator(
        pipelines.owner_test_chat_pipeline, storage_scope
    )
    assemble_assistant_version_operator = pipeline_operator(
        pipelines.assemble_assistant_version_pipeline, storage_scope
    )
    telegram_webhook_operator = pipeline_operator(
        pipelines.telegram_webhook_pipeline, storage_scope
    )
    meta_webhook_operator = pipeline_operator(
        pipelines.meta_webhook_pipeline, storage_scope
    )
    widget_message_operator = pipeline_operator(
        pipelines.widget_message_pipeline, storage_scope
    )
    call_forwarding_instructions_operator = pipeline_operator(
        pipelines.call_forwarding_instructions_pipeline, storage_scope
    )
    run_autotests_operator = pipeline_operator(
        pipelines.run_autotests_pipeline, storage_scope
    )
    run_queued_autotests_operator = pipeline_operator(
        pipelines.run_queued_autotests_pipeline, storage_scope
    )
    voice_tool_webhook_operator = pipeline_operator(
        pipelines.voice_tool_webhook_pipeline, storage_scope
    )
    post_call_webhook_operator = pipeline_operator(
        pipelines.post_call_webhook_pipeline, storage_scope
    )
    purge_expired_recordings_operator = pipeline_operator(
        pipelines.purge_expired_recordings_pipeline, storage_scope
    )

    # --- One use case per endpoint or job.

    # --- Catalog.
    list_countries_operator = pipeline_operator(
        pipelines.list_countries_pipeline, storage_scope
    )
    get_country_profile_operator = pipeline_operator(
        pipelines.get_country_profile_pipeline, storage_scope
    )
    list_languages_operator = pipeline_operator(
        pipelines.list_languages_pipeline, storage_scope
    )
    quote_plans_operator = pipeline_operator(
        pipelines.quote_plans_pipeline, storage_scope
    )
    parse_phone_number_operator = pipeline_operator(
        pipelines.parse_phone_number_pipeline, storage_scope
    )

    # --- Sign-in and the current user.
    authenticate_user_operator = pipeline_operator(
        pipelines.authenticate_user_pipeline, storage_scope
    )
    start_otp_login_operator = pipeline_operator(
        pipelines.start_otp_login_pipeline, storage_scope
    )
    verify_otp_login_operator = pipeline_operator(
        pipelines.verify_otp_login_pipeline, storage_scope
    )
    logout_operator = pipeline_operator(pipelines.logout_pipeline, storage_scope)
    get_current_user_operator = pipeline_operator(
        pipelines.get_current_user_pipeline, storage_scope
    )
    update_current_user_operator = pipeline_operator(
        pipelines.update_current_user_pipeline, storage_scope
    )

    # --- Businesses and teams.
    authorize_business_access_operator = pipeline_operator(
        pipelines.authorize_business_access_pipeline, storage_scope
    )
    create_business_operator = pipeline_operator(
        pipelines.create_business_pipeline, storage_scope
    )
    list_my_businesses_operator = pipeline_operator(
        pipelines.list_my_businesses_pipeline, storage_scope
    )
    get_business_operator = pipeline_operator(
        pipelines.get_business_pipeline, storage_scope
    )
    update_business_settings_operator = pipeline_operator(
        pipelines.update_business_settings_pipeline, storage_scope
    )
    invite_staff_operator = pipeline_operator(
        pipelines.invite_staff_pipeline, storage_scope
    )
    remove_member_operator = pipeline_operator(
        pipelines.remove_member_pipeline, storage_scope
    )
    change_member_role_operator = pipeline_operator(
        pipelines.change_member_role_pipeline, storage_scope
    )

    # --- Compliance.
    get_dpa_status_operator = pipeline_operator(
        pipelines.get_dpa_status_pipeline, storage_scope
    )
    accept_dpa_operator = pipeline_operator(
        pipelines.accept_dpa_pipeline, storage_scope
    )
    list_audit_log_operator = pipeline_operator(
        pipelines.list_audit_log_pipeline, storage_scope
    )
    export_contact_data_operator = pipeline_operator(
        pipelines.export_contact_data_pipeline, storage_scope
    )
    delete_contact_data_operator = pipeline_operator(
        pipelines.delete_contact_data_pipeline, storage_scope
    )
    get_dpa_document_operator = pipeline_operator(
        pipelines.get_dpa_document_pipeline, storage_scope
    )
    list_contacts_operator = pipeline_operator(
        pipelines.list_contacts_pipeline, storage_scope
    )
    get_contact_operator = pipeline_operator(
        pipelines.get_contact_pipeline, storage_scope
    )

    # --- Niche templates and the profile wizard.
    list_niche_templates_operator = pipeline_operator(
        pipelines.list_niche_templates_pipeline, storage_scope
    )
    get_niche_template_operator = pipeline_operator(
        pipelines.get_niche_template_pipeline, storage_scope
    )
    get_profile_wizard_operator = pipeline_operator(
        pipelines.get_profile_wizard_pipeline, storage_scope
    )
    get_business_profile_operator = pipeline_operator(
        pipelines.get_business_profile_pipeline, storage_scope
    )
    save_profile_operator = pipeline_operator(
        pipelines.save_profile_pipeline, storage_scope
    )
    save_profile_step_operator = pipeline_operator(
        pipelines.save_profile_step_pipeline, storage_scope
    )
    compute_profile_gaps_operator = pipeline_operator(
        pipelines.compute_profile_gaps_pipeline, storage_scope
    )

    # --- Knowledge base.
    list_knowledge_items_operator = pipeline_operator(
        pipelines.list_knowledge_items_pipeline, storage_scope
    )
    create_knowledge_item_operator = pipeline_operator(
        pipelines.create_knowledge_item_pipeline, storage_scope
    )
    get_knowledge_item_operator = pipeline_operator(
        pipelines.get_knowledge_item_pipeline, storage_scope
    )
    update_knowledge_item_operator = pipeline_operator(
        pipelines.update_knowledge_item_pipeline, storage_scope
    )
    delete_knowledge_item_operator = pipeline_operator(
        pipelines.delete_knowledge_item_pipeline, storage_scope
    )
    search_knowledge_operator = pipeline_operator(
        pipelines.search_knowledge_pipeline, storage_scope
    )

    # --- Resources and schedule exceptions.
    list_resources_operator = pipeline_operator(
        pipelines.list_resources_pipeline, storage_scope
    )
    create_resource_operator = pipeline_operator(
        pipelines.create_resource_pipeline, storage_scope
    )
    update_resource_operator = pipeline_operator(
        pipelines.update_resource_pipeline, storage_scope
    )
    list_schedule_exceptions_operator = pipeline_operator(
        pipelines.list_schedule_exceptions_pipeline, storage_scope
    )
    create_schedule_exception_operator = pipeline_operator(
        pipelines.create_schedule_exception_pipeline, storage_scope
    )
    delete_schedule_exception_operator = pipeline_operator(
        pipelines.delete_schedule_exception_pipeline, storage_scope
    )

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_operator = pipeline_operator(
        pipelines.check_availability_pipeline, storage_scope
    )
    list_bookings_operator = pipeline_operator(
        pipelines.list_bookings_pipeline, storage_scope
    )
    create_manual_booking_operator = pipeline_operator(
        pipelines.create_manual_booking_pipeline, storage_scope
    )
    cancel_booking_operator = pipeline_operator(
        pipelines.cancel_booking_pipeline, storage_scope
    )
    reschedule_booking_operator = pipeline_operator(
        pipelines.reschedule_booking_pipeline, storage_scope
    )
    update_booking_status_operator = pipeline_operator(
        pipelines.update_booking_status_pipeline, storage_scope
    )
    list_leads_operator = pipeline_operator(
        pipelines.list_leads_pipeline, storage_scope
    )
    update_lead_status_operator = pipeline_operator(
        pipelines.update_lead_status_pipeline, storage_scope
    )
    list_handoffs_operator = pipeline_operator(
        pipelines.list_handoffs_pipeline, storage_scope
    )
    resolve_handoff_operator = pipeline_operator(
        pipelines.resolve_handoff_pipeline, storage_scope
    )
    list_unanswered_questions_operator = pipeline_operator(
        pipelines.list_unanswered_questions_pipeline, storage_scope
    )
    answer_unanswered_question_operator = pipeline_operator(
        pipelines.answer_unanswered_question_pipeline, storage_scope
    )
    get_dashboard_stats_operator = pipeline_operator(
        pipelines.get_dashboard_stats_pipeline, storage_scope
    )
    start_google_calendar_connection_operator = pipeline_operator(
        pipelines.start_google_calendar_connection_pipeline, storage_scope
    )
    complete_google_calendar_connection_operator = pipeline_operator(
        pipelines.complete_google_calendar_connection_pipeline, storage_scope
    )
    disconnect_google_calendar_operator = pipeline_operator(
        pipelines.disconnect_google_calendar_pipeline, storage_scope
    )

    # --- Conversation feed and menu import.
    list_conversations_operator = pipeline_operator(
        pipelines.list_conversations_pipeline, storage_scope
    )
    get_conversation_operator = pipeline_operator(
        pipelines.get_conversation_pipeline, storage_scope
    )
    rate_conversation_operator = pipeline_operator(
        pipelines.rate_conversation_pipeline, storage_scope
    )
    import_menu_operator = pipeline_operator(
        pipelines.import_menu_pipeline, storage_scope
    )
    confirm_imported_items_operator = pipeline_operator(
        pipelines.confirm_imported_items_pipeline, storage_scope
    )

    # --- Assistant versions and autotests.
    list_assistant_versions_operator = pipeline_operator(
        pipelines.list_assistant_versions_pipeline, storage_scope
    )
    get_assistant_version_operator = pipeline_operator(
        pipelines.get_assistant_version_pipeline, storage_scope
    )
    get_autotest_run_operator = pipeline_operator(
        pipelines.get_autotest_run_pipeline, storage_scope
    )
    publish_assistant_version_operator = pipeline_operator(
        pipelines.publish_assistant_version_pipeline, storage_scope
    )
    rollback_assistant_version_operator = pipeline_operator(
        pipelines.rollback_assistant_version_pipeline, storage_scope
    )

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_operator = pipeline_operator(
        pipelines.verify_meta_webhook_pipeline, storage_scope
    )
    handle_platform_bot_update_operator = pipeline_operator(
        pipelines.handle_platform_bot_update_pipeline, storage_scope
    )
    get_widget_config_operator = pipeline_operator(
        pipelines.get_widget_config_pipeline, storage_scope
    )
    list_channels_operator = pipeline_operator(
        pipelines.list_channels_pipeline, storage_scope
    )
    connect_channel_operator = pipeline_operator(
        pipelines.connect_channel_pipeline, storage_scope
    )
    disable_channel_operator = pipeline_operator(
        pipelines.disable_channel_pipeline, storage_scope
    )
    get_widget_snippet_operator = pipeline_operator(
        pipelines.get_widget_snippet_pipeline, storage_scope
    )
    create_telegram_link_operator = pipeline_operator(
        pipelines.create_telegram_link_pipeline, storage_scope
    )
    configure_platform_bot_webhook_operator = pipeline_operator(
        pipelines.configure_platform_bot_webhook_pipeline, storage_scope
    )

    # --- Voice webhooks.
    start_voice_call_operator = pipeline_operator(
        pipelines.start_voice_call_pipeline, storage_scope
    )

    # --- Billing and payments.
    get_billing_overview_operator = pipeline_operator(
        pipelines.get_billing_overview_pipeline, storage_scope
    )
    start_trial_operator = pipeline_operator(
        pipelines.start_trial_pipeline, storage_scope
    )
    change_plan_operator = pipeline_operator(
        pipelines.change_plan_pipeline, storage_scope
    )
    cancel_subscription_operator = pipeline_operator(
        pipelines.cancel_subscription_pipeline, storage_scope
    )
    start_checkout_operator = pipeline_operator(
        pipelines.start_checkout_pipeline, storage_scope
    )
    subscribe_operator = pipeline_operator(pipelines.subscribe_pipeline, storage_scope)
    process_payment_webhook_operator = pipeline_operator(
        pipelines.process_payment_webhook_pipeline, storage_scope
    )

    # --- Platform admin.
    list_clients_operator = pipeline_operator(
        pipelines.list_clients_pipeline, storage_scope
    )
    get_client_health_operator = pipeline_operator(
        pipelines.get_client_health_pipeline, storage_scope
    )
    open_client_cabinet_operator = pipeline_operator(
        pipelines.open_client_cabinet_pipeline, storage_scope
    )

    # --- Periodic jobs of the background worker.
    end_trials_operator = pipeline_operator(
        pipelines.end_trials_pipeline, storage_scope
    )
    enforce_grace_periods_operator = pipeline_operator(
        pipelines.enforce_grace_periods_pipeline, storage_scope
    )
    check_package_usage_operator = pipeline_operator(
        pipelines.check_package_usage_pipeline, storage_scope
    )
    invoice_usage_overage_operator = pipeline_operator(
        pipelines.invoice_usage_overage_pipeline, storage_scope
    )
    send_booking_reminders_operator = pipeline_operator(
        pipelines.send_booking_reminders_pipeline, storage_scope
    )
    flush_llm_traces_operator = pipeline_operator(
        pipelines.flush_llm_traces_pipeline, storage_scope
    )

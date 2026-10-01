from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines import PipelinesContainer
from app.containers.provider_chains import pipeline_operator


class OperatorsContainer(containers.DeclarativeContainer):
    """
    One operator per HTTP endpoint and per worker job. Each runs its
    pipeline synchronously; input and output types come from the use case
    or orchestrator at the bottom of the chain.
    """

    pipelines: PipelinesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Dedicated pipelines and orchestrators.
    owner_test_chat_operator = pipeline_operator(pipelines.owner_test_chat_pipeline)
    assemble_assistant_version_operator = pipeline_operator(
        pipelines.assemble_assistant_version_pipeline
    )
    telegram_webhook_operator = pipeline_operator(pipelines.telegram_webhook_pipeline)
    meta_webhook_operator = pipeline_operator(pipelines.meta_webhook_pipeline)
    widget_message_operator = pipeline_operator(pipelines.widget_message_pipeline)
    call_forwarding_instructions_operator = pipeline_operator(
        pipelines.call_forwarding_instructions_pipeline
    )
    run_autotests_operator = pipeline_operator(pipelines.run_autotests_pipeline)
    voice_tool_webhook_operator = pipeline_operator(
        pipelines.voice_tool_webhook_pipeline
    )
    post_call_webhook_operator = pipeline_operator(pipelines.post_call_webhook_pipeline)
    purge_expired_recordings_operator = pipeline_operator(
        pipelines.purge_expired_recordings_pipeline
    )

    # --- One use case per endpoint or job.

    # --- Catalog.
    list_countries_operator = pipeline_operator(pipelines.list_countries_pipeline)
    get_country_profile_operator = pipeline_operator(
        pipelines.get_country_profile_pipeline
    )
    list_languages_operator = pipeline_operator(pipelines.list_languages_pipeline)
    quote_plans_operator = pipeline_operator(pipelines.quote_plans_pipeline)
    parse_phone_number_operator = pipeline_operator(
        pipelines.parse_phone_number_pipeline
    )

    # --- Sign-in and the current user.
    authenticate_user_operator = pipeline_operator(pipelines.authenticate_user_pipeline)
    start_otp_login_operator = pipeline_operator(pipelines.start_otp_login_pipeline)
    verify_otp_login_operator = pipeline_operator(pipelines.verify_otp_login_pipeline)
    logout_operator = pipeline_operator(pipelines.logout_pipeline)
    get_current_user_operator = pipeline_operator(pipelines.get_current_user_pipeline)
    update_current_user_operator = pipeline_operator(
        pipelines.update_current_user_pipeline
    )

    # --- Businesses and teams.
    authorize_business_access_operator = pipeline_operator(
        pipelines.authorize_business_access_pipeline
    )
    create_business_operator = pipeline_operator(pipelines.create_business_pipeline)
    list_my_businesses_operator = pipeline_operator(
        pipelines.list_my_businesses_pipeline
    )
    get_business_operator = pipeline_operator(pipelines.get_business_pipeline)
    update_business_settings_operator = pipeline_operator(
        pipelines.update_business_settings_pipeline
    )
    invite_staff_operator = pipeline_operator(pipelines.invite_staff_pipeline)
    remove_member_operator = pipeline_operator(pipelines.remove_member_pipeline)

    # --- Compliance.
    get_dpa_status_operator = pipeline_operator(pipelines.get_dpa_status_pipeline)
    accept_dpa_operator = pipeline_operator(pipelines.accept_dpa_pipeline)
    list_audit_log_operator = pipeline_operator(pipelines.list_audit_log_pipeline)
    export_contact_data_operator = pipeline_operator(
        pipelines.export_contact_data_pipeline
    )
    delete_contact_data_operator = pipeline_operator(
        pipelines.delete_contact_data_pipeline
    )

    # --- Niche templates and the profile wizard.
    list_niche_templates_operator = pipeline_operator(
        pipelines.list_niche_templates_pipeline
    )
    get_niche_template_operator = pipeline_operator(
        pipelines.get_niche_template_pipeline
    )
    get_profile_wizard_operator = pipeline_operator(
        pipelines.get_profile_wizard_pipeline
    )
    get_business_profile_operator = pipeline_operator(
        pipelines.get_business_profile_pipeline
    )
    save_profile_operator = pipeline_operator(pipelines.save_profile_pipeline)
    save_profile_step_operator = pipeline_operator(pipelines.save_profile_step_pipeline)
    compute_profile_gaps_operator = pipeline_operator(
        pipelines.compute_profile_gaps_pipeline
    )

    # --- Knowledge base.
    list_knowledge_items_operator = pipeline_operator(
        pipelines.list_knowledge_items_pipeline
    )
    create_knowledge_item_operator = pipeline_operator(
        pipelines.create_knowledge_item_pipeline
    )
    get_knowledge_item_operator = pipeline_operator(
        pipelines.get_knowledge_item_pipeline
    )
    update_knowledge_item_operator = pipeline_operator(
        pipelines.update_knowledge_item_pipeline
    )
    delete_knowledge_item_operator = pipeline_operator(
        pipelines.delete_knowledge_item_pipeline
    )
    search_knowledge_operator = pipeline_operator(pipelines.search_knowledge_pipeline)

    # --- Resources and schedule exceptions.
    list_resources_operator = pipeline_operator(pipelines.list_resources_pipeline)
    create_resource_operator = pipeline_operator(pipelines.create_resource_pipeline)
    update_resource_operator = pipeline_operator(pipelines.update_resource_pipeline)
    list_schedule_exceptions_operator = pipeline_operator(
        pipelines.list_schedule_exceptions_pipeline
    )
    create_schedule_exception_operator = pipeline_operator(
        pipelines.create_schedule_exception_pipeline
    )
    delete_schedule_exception_operator = pipeline_operator(
        pipelines.delete_schedule_exception_pipeline
    )

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_operator = pipeline_operator(
        pipelines.check_availability_pipeline
    )
    list_bookings_operator = pipeline_operator(pipelines.list_bookings_pipeline)
    create_manual_booking_operator = pipeline_operator(
        pipelines.create_manual_booking_pipeline
    )
    cancel_booking_operator = pipeline_operator(pipelines.cancel_booking_pipeline)
    reschedule_booking_operator = pipeline_operator(
        pipelines.reschedule_booking_pipeline
    )
    update_booking_status_operator = pipeline_operator(
        pipelines.update_booking_status_pipeline
    )
    list_leads_operator = pipeline_operator(pipelines.list_leads_pipeline)
    update_lead_status_operator = pipeline_operator(
        pipelines.update_lead_status_pipeline
    )
    list_handoffs_operator = pipeline_operator(pipelines.list_handoffs_pipeline)
    resolve_handoff_operator = pipeline_operator(pipelines.resolve_handoff_pipeline)
    list_unanswered_questions_operator = pipeline_operator(
        pipelines.list_unanswered_questions_pipeline
    )
    answer_unanswered_question_operator = pipeline_operator(
        pipelines.answer_unanswered_question_pipeline
    )
    get_dashboard_stats_operator = pipeline_operator(
        pipelines.get_dashboard_stats_pipeline
    )
    start_google_calendar_connection_operator = pipeline_operator(
        pipelines.start_google_calendar_connection_pipeline
    )
    complete_google_calendar_connection_operator = pipeline_operator(
        pipelines.complete_google_calendar_connection_pipeline
    )
    disconnect_google_calendar_operator = pipeline_operator(
        pipelines.disconnect_google_calendar_pipeline
    )

    # --- Conversation feed and menu import.
    list_conversations_operator = pipeline_operator(
        pipelines.list_conversations_pipeline
    )
    get_conversation_operator = pipeline_operator(pipelines.get_conversation_pipeline)
    import_menu_operator = pipeline_operator(pipelines.import_menu_pipeline)
    confirm_imported_items_operator = pipeline_operator(
        pipelines.confirm_imported_items_pipeline
    )

    # --- Assistant versions and autotests.
    list_assistant_versions_operator = pipeline_operator(
        pipelines.list_assistant_versions_pipeline
    )
    get_assistant_version_operator = pipeline_operator(
        pipelines.get_assistant_version_pipeline
    )
    get_autotest_run_operator = pipeline_operator(pipelines.get_autotest_run_pipeline)
    publish_assistant_version_operator = pipeline_operator(
        pipelines.publish_assistant_version_pipeline
    )
    rollback_assistant_version_operator = pipeline_operator(
        pipelines.rollback_assistant_version_pipeline
    )

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_operator = pipeline_operator(
        pipelines.verify_meta_webhook_pipeline
    )
    handle_platform_bot_update_operator = pipeline_operator(
        pipelines.handle_platform_bot_update_pipeline
    )
    get_widget_config_operator = pipeline_operator(pipelines.get_widget_config_pipeline)
    list_channels_operator = pipeline_operator(pipelines.list_channels_pipeline)
    connect_channel_operator = pipeline_operator(pipelines.connect_channel_pipeline)
    disable_channel_operator = pipeline_operator(pipelines.disable_channel_pipeline)
    get_widget_snippet_operator = pipeline_operator(
        pipelines.get_widget_snippet_pipeline
    )
    create_telegram_link_operator = pipeline_operator(
        pipelines.create_telegram_link_pipeline
    )
    configure_platform_bot_webhook_operator = pipeline_operator(
        pipelines.configure_platform_bot_webhook_pipeline
    )

    # --- Voice webhooks.
    start_voice_call_operator = pipeline_operator(pipelines.start_voice_call_pipeline)

    # --- Billing and payments.
    get_billing_overview_operator = pipeline_operator(
        pipelines.get_billing_overview_pipeline
    )
    start_trial_operator = pipeline_operator(pipelines.start_trial_pipeline)
    change_plan_operator = pipeline_operator(pipelines.change_plan_pipeline)
    cancel_subscription_operator = pipeline_operator(
        pipelines.cancel_subscription_pipeline
    )
    start_checkout_operator = pipeline_operator(pipelines.start_checkout_pipeline)
    process_payment_webhook_operator = pipeline_operator(
        pipelines.process_payment_webhook_pipeline
    )

    # --- Platform admin.
    list_clients_operator = pipeline_operator(pipelines.list_clients_pipeline)
    get_client_health_operator = pipeline_operator(pipelines.get_client_health_pipeline)
    open_client_cabinet_operator = pipeline_operator(
        pipelines.open_client_cabinet_pipeline
    )

    # --- Periodic jobs of the background worker.
    end_trials_operator = pipeline_operator(pipelines.end_trials_pipeline)
    enforce_grace_periods_operator = pipeline_operator(
        pipelines.enforce_grace_periods_pipeline
    )
    check_package_usage_operator = pipeline_operator(
        pipelines.check_package_usage_pipeline
    )
    send_booking_reminders_operator = pipeline_operator(
        pipelines.send_booking_reminders_pipeline
    )
    flush_llm_traces_operator = pipeline_operator(pipelines.flush_llm_traces_pipeline)

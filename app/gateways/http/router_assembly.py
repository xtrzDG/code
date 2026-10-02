"""Every HTTP router of the API, built from the container's operators."""

from fastapi import APIRouter

from app.containers.app import AppContainer
from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_jobs_routes import build_admin_jobs_router
from app.gateways.http.admin_routes import build_admin_router
from app.gateways.http.assistant_routes import build_assistant_router
from app.gateways.http.billing_routes import build_billing_router
from app.gateways.http.business_routes import build_business_router
from app.gateways.http.catalog_routes import build_catalog_router
from app.gateways.http.channel_routes import build_channel_router
from app.gateways.http.channel_settings_routes import build_channel_settings_router
from app.gateways.http.compliance_routes import build_compliance_router
from app.gateways.http.conversation_routes import build_conversation_router
from app.gateways.http.events_routes import build_events_router
from app.gateways.http.health_routes import build_readiness_router
from app.gateways.http.knowledge_routes import build_knowledge_router
from app.gateways.http.menu_import_routes import build_menu_import_router
from app.gateways.http.operations_routes import build_operations_router
from app.gateways.http.profile_routes import build_profile_router
from app.gateways.http.resource_routes import build_resource_router
from app.gateways.http.user_authentication import (
    CurrentUserDependency,
    build_current_user_dependency,
)
from app.gateways.http.users_routes import build_users_router
from app.gateways.http.voice_routes import build_voice_router
from app.gateways.http.widget_error_routes import build_widget_error_router
from app.gateways.http.widget_script_routes import build_widget_script_router


def build_application_routers(app_container: AppContainer) -> list[APIRouter]:
    """
    Routers of every module, sharing one bearer-token dependency.

    Operators are built once here; their use cases are stateless and the
    stateful collaborators (locks, caches, storage) are container singletons.
    """

    operators: OperatorsContainer = app_container.operators
    accounts = operators.accounts
    compliance = operators.compliance
    knowledge = operators.knowledge
    operations = operators.operations
    conversations = operators.conversations
    assistants = operators.assistants
    channels = operators.channels
    billing = operators.billing
    platform = operators.platform
    current_user: CurrentUserDependency = build_current_user_dependency(
        accounts.authenticate_user_operator()
    )
    business_access_operator = accounts.authorize_business_access_operator()
    return [
        build_catalog_router(
            list_countries_operator=accounts.list_countries_operator(),
            get_country_profile_operator=accounts.get_country_profile_operator(),
            list_languages_operator=accounts.list_languages_operator(),
            quote_plans_operator=accounts.quote_plans_operator(),
            parse_phone_number_operator=accounts.parse_phone_number_operator(),
            call_forwarding_instructions_operator=(
                accounts.call_forwarding_instructions_operator()
            ),
            current_user=current_user,
        ),
        build_users_router(
            start_otp_login_operator=accounts.start_otp_login_operator(),
            get_login_options_operator=accounts.get_login_options_operator(),
            verify_otp_login_operator=accounts.verify_otp_login_operator(),
            logout_operator=accounts.logout_operator(),
            get_current_user_operator=accounts.get_current_user_operator(),
            update_current_user_operator=accounts.update_current_user_operator(),
            current_user=current_user,
        ),
        build_business_router(
            create_business_operator=accounts.create_business_operator(),
            list_my_businesses_operator=accounts.list_my_businesses_operator(),
            get_business_operator=accounts.get_business_operator(),
            update_business_settings_operator=(
                accounts.update_business_settings_operator()
            ),
            invite_staff_operator=accounts.invite_staff_operator(),
            remove_member_operator=accounts.remove_member_operator(),
            change_member_role_operator=accounts.change_member_role_operator(),
            current_user=current_user,
        ),
        build_compliance_router(
            get_dpa_status_operator=compliance.get_dpa_status_operator(),
            accept_dpa_operator=compliance.accept_dpa_operator(),
            list_audit_log_operator=compliance.list_audit_log_operator(),
            export_contact_data_operator=compliance.export_contact_data_operator(),
            delete_contact_data_operator=compliance.delete_contact_data_operator(),
            list_contacts_operator=compliance.list_contacts_operator(),
            get_contact_operator=compliance.get_contact_operator(),
            get_dpa_document_operator=compliance.get_dpa_document_operator(),
            current_user=current_user,
        ),
        build_profile_router(
            current_user=current_user,
            business_access_operator=business_access_operator,
            list_niche_templates_operator=knowledge.list_niche_templates_operator(),
            get_niche_template_operator=knowledge.get_niche_template_operator(),
            get_profile_wizard_operator=knowledge.get_profile_wizard_operator(),
            get_business_profile_operator=knowledge.get_business_profile_operator(),
            save_profile_operator=knowledge.save_profile_operator(),
            save_profile_step_operator=knowledge.save_profile_step_operator(),
            compute_profile_gaps_operator=knowledge.compute_profile_gaps_operator(),
        ),
        build_knowledge_router(
            current_user=current_user,
            business_access_operator=business_access_operator,
            list_knowledge_items_operator=knowledge.list_knowledge_items_operator(),
            create_knowledge_item_operator=knowledge.create_knowledge_item_operator(),
            get_knowledge_item_operator=knowledge.get_knowledge_item_operator(),
            update_knowledge_item_operator=knowledge.update_knowledge_item_operator(),
            delete_knowledge_item_operator=knowledge.delete_knowledge_item_operator(),
            search_knowledge_operator=knowledge.search_knowledge_operator(),
        ),
        build_menu_import_router(
            import_menu_operator=knowledge.import_menu_operator(),
            confirm_imported_items_operator=knowledge.confirm_imported_items_operator(),
            discard_import_batch_operator=knowledge.discard_import_batch_operator(),
            current_user=current_user,
        ),
        build_resource_router(
            current_user=current_user,
            business_access_operator=business_access_operator,
            list_resources_operator=knowledge.list_resources_operator(),
            create_resource_operator=knowledge.create_resource_operator(),
            update_resource_operator=knowledge.update_resource_operator(),
            list_schedule_exceptions_operator=(
                knowledge.list_schedule_exceptions_operator()
            ),
            create_schedule_exception_operator=(
                knowledge.create_schedule_exception_operator()
            ),
            delete_schedule_exception_operator=(
                knowledge.delete_schedule_exception_operator()
            ),
        ),
        build_operations_router(
            current_user=current_user,
            authorize_business_access=business_access_operator,
            check_availability=operations.check_availability_operator(),
            list_bookings=operations.list_bookings_operator(),
            create_manual_booking=operations.create_manual_booking_operator(),
            cancel_booking=operations.cancel_booking_operator(),
            reschedule_booking=operations.reschedule_booking_operator(),
            update_booking=operations.update_booking_operator(),
            list_leads=operations.list_leads_operator(),
            update_lead_status=operations.update_lead_status_operator(),
            list_handoffs=operations.list_handoffs_operator(),
            resolve_handoff=operations.resolve_handoff_operator(),
            list_unanswered_questions=operations.list_unanswered_questions_operator(),
            answer_unanswered_question=operations.answer_unanswered_question_operator(),
            get_dashboard_stats=operations.get_dashboard_stats_operator(),
            get_inbox_counts=operations.get_inbox_counts_operator(),
            start_calendar_connection=(
                operations.start_google_calendar_connection_operator()
            ),
            complete_calendar_connection=(
                operations.complete_google_calendar_connection_operator()
            ),
            disconnect_calendar=operations.disconnect_google_calendar_operator(),
            get_calendar_connection=(
                operations.get_google_calendar_connection_operator()
            ),
            cabinet_base_url=app_container.config.app_settings().cabinet_base_url,
        ),
        build_events_router(
            current_user=current_user,
            authorize_business_access=business_access_operator,
            get_attention_counts=operations.get_attention_counts_operator(),
            stream_facilitator=app_container.facilitators.live_stream_facilitator(),
            limits=app_container.facilitators.live_stream_limits(),
        ),
        build_conversation_router(
            list_conversations_operator=conversations.list_conversations_operator(),
            get_conversation_operator=conversations.get_conversation_operator(),
            owner_test_chat_operator=conversations.owner_test_chat_operator(),
            rate_conversation_operator=conversations.rate_conversation_operator(),
            current_user=current_user,
            send_staff_message_operator=conversations.send_staff_message_operator(),
            get_call_recording_operator=conversations.get_call_recording_operator(),
        ),
        build_assistant_router(
            assemble_assistant_version_operator=(
                assistants.assemble_assistant_version_operator()
            ),
            list_assistant_versions_operator=(
                assistants.list_assistant_versions_operator()
            ),
            get_assistant_version_operator=assistants.get_assistant_version_operator(),
            get_autotest_run_operator=assistants.get_autotest_run_operator(),
            get_go_live_readiness_operator=assistants.get_go_live_readiness_operator(),
            run_autotests_operator=assistants.run_autotests_operator(),
            publish_assistant_version_operator=(
                assistants.publish_assistant_version_operator()
            ),
            rollback_assistant_version_operator=(
                assistants.rollback_assistant_version_operator()
            ),
            current_user=current_user,
        ),
        build_channel_router(
            telegram_webhook_operator=channels.telegram_webhook_operator(),
            meta_webhook_verification_operator=channels.verify_meta_webhook_operator(),
            meta_webhook_operator=channels.meta_webhook_operator(),
            platform_bot_webhook_operator=(
                channels.handle_platform_bot_update_operator()
            ),
            widget_config_operator=channels.get_widget_config_operator(),
            widget_message_operator=channels.widget_message_operator(),
            widget_messages_operator=channels.get_widget_messages_operator(),
        ),
        build_channel_settings_router(
            list_channels_operator=channels.list_channels_operator(),
            connect_channel_operator=channels.connect_channel_operator(),
            disable_channel_operator=channels.disable_channel_operator(),
            widget_snippet_operator=channels.get_widget_snippet_operator(),
            create_telegram_link_operator=channels.create_telegram_link_operator(),
            current_user=current_user,
            set_whatsapp_staff_template_operator=(
                channels.set_whatsapp_staff_template_operator()
            ),
        ),
        build_voice_router(
            voice_tool_operator=conversations.voice_tool_webhook_operator(),
            call_initiation_operator=conversations.start_voice_call_operator(),
            post_call_operator=conversations.post_call_webhook_operator(),
        ),
        build_billing_router(
            get_billing_overview_operator=billing.get_billing_overview_operator(),
            start_trial_operator=billing.start_trial_operator(),
            change_plan_operator=billing.change_plan_operator(),
            cancel_subscription_operator=billing.cancel_subscription_operator(),
            start_checkout_operator=billing.start_checkout_operator(),
            subscribe_operator=billing.subscribe_operator(),
            payment_webhook_operator=billing.process_payment_webhook_operator(),
            current_user=current_user,
        ),
        build_admin_router(
            list_clients_operator=platform.list_clients_operator(),
            get_client_health_operator=platform.get_client_health_operator(),
            open_client_cabinet_operator=platform.open_client_cabinet_operator(),
            current_user=current_user,
        ),
        build_admin_jobs_router(
            list_queued_jobs_operator=platform.list_queued_jobs_operator(),
            retry_queued_job_operator=platform.retry_queued_job_operator(),
            discard_queued_job_operator=platform.discard_queued_job_operator(),
            current_user=current_user,
        ),
        build_widget_script_router(),
        build_readiness_router(platform.check_readiness_operator()),
        build_widget_error_router(platform.report_widget_error_operator()),
    ]

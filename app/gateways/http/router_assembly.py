"""Every HTTP router of the API, built from the container's operators."""

from fastapi import APIRouter

from app.containers.app import AppContainer
from app.containers.operators import OperatorsContainer
from app.gateways.http.admin_routes import build_admin_router
from app.gateways.http.assistant_routes import build_assistant_router
from app.gateways.http.billing_routes import build_billing_router
from app.gateways.http.business_routes import build_business_router
from app.gateways.http.catalog_routes import build_catalog_router
from app.gateways.http.channel_routes import build_channel_router
from app.gateways.http.channel_settings_routes import build_channel_settings_router
from app.gateways.http.compliance_routes import build_compliance_router
from app.gateways.http.conversation_routes import build_conversation_router
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
from app.gateways.http.widget_script_routes import build_widget_script_router


def build_application_routers(app_container: AppContainer) -> list[APIRouter]:
    """
    Routers of every module, sharing one bearer-token dependency.

    Operators are built once here; their use cases are stateless and the
    stateful collaborators (locks, caches, storage) are container singletons.
    """

    operators: OperatorsContainer = app_container.operators
    current_user: CurrentUserDependency = build_current_user_dependency(
        operators.authenticate_user_operator()
    )
    business_access_operator = operators.authorize_business_access_operator()
    return [
        build_catalog_router(
            list_countries_operator=operators.list_countries_operator(),
            get_country_profile_operator=operators.get_country_profile_operator(),
            list_languages_operator=operators.list_languages_operator(),
            quote_plans_operator=operators.quote_plans_operator(),
            parse_phone_number_operator=operators.parse_phone_number_operator(),
            call_forwarding_instructions_operator=(
                operators.call_forwarding_instructions_operator()
            ),
            current_user=current_user,
        ),
        build_users_router(
            start_otp_login_operator=operators.start_otp_login_operator(),
            verify_otp_login_operator=operators.verify_otp_login_operator(),
            logout_operator=operators.logout_operator(),
            get_current_user_operator=operators.get_current_user_operator(),
            update_current_user_operator=operators.update_current_user_operator(),
            current_user=current_user,
        ),
        build_business_router(
            create_business_operator=operators.create_business_operator(),
            list_my_businesses_operator=operators.list_my_businesses_operator(),
            get_business_operator=operators.get_business_operator(),
            update_business_settings_operator=(
                operators.update_business_settings_operator()
            ),
            invite_staff_operator=operators.invite_staff_operator(),
            remove_member_operator=operators.remove_member_operator(),
            current_user=current_user,
        ),
        build_compliance_router(
            get_dpa_status_operator=operators.get_dpa_status_operator(),
            accept_dpa_operator=operators.accept_dpa_operator(),
            list_audit_log_operator=operators.list_audit_log_operator(),
            export_contact_data_operator=operators.export_contact_data_operator(),
            delete_contact_data_operator=operators.delete_contact_data_operator(),
            current_user=current_user,
        ),
        build_profile_router(
            current_user=current_user,
            business_access_operator=business_access_operator,
            list_niche_templates_operator=operators.list_niche_templates_operator(),
            get_niche_template_operator=operators.get_niche_template_operator(),
            get_profile_wizard_operator=operators.get_profile_wizard_operator(),
            get_business_profile_operator=operators.get_business_profile_operator(),
            save_profile_operator=operators.save_profile_operator(),
            save_profile_step_operator=operators.save_profile_step_operator(),
            compute_profile_gaps_operator=operators.compute_profile_gaps_operator(),
        ),
        build_knowledge_router(
            current_user=current_user,
            business_access_operator=business_access_operator,
            list_knowledge_items_operator=operators.list_knowledge_items_operator(),
            create_knowledge_item_operator=operators.create_knowledge_item_operator(),
            get_knowledge_item_operator=operators.get_knowledge_item_operator(),
            update_knowledge_item_operator=operators.update_knowledge_item_operator(),
            delete_knowledge_item_operator=operators.delete_knowledge_item_operator(),
            search_knowledge_operator=operators.search_knowledge_operator(),
        ),
        build_menu_import_router(
            import_menu_operator=operators.import_menu_operator(),
            confirm_imported_items_operator=operators.confirm_imported_items_operator(),
            current_user=current_user,
        ),
        build_resource_router(
            current_user=current_user,
            business_access_operator=business_access_operator,
            list_resources_operator=operators.list_resources_operator(),
            create_resource_operator=operators.create_resource_operator(),
            update_resource_operator=operators.update_resource_operator(),
            list_schedule_exceptions_operator=(
                operators.list_schedule_exceptions_operator()
            ),
            create_schedule_exception_operator=(
                operators.create_schedule_exception_operator()
            ),
            delete_schedule_exception_operator=(
                operators.delete_schedule_exception_operator()
            ),
        ),
        build_operations_router(
            current_user=current_user,
            authorize_business_access=business_access_operator,
            check_availability=operators.check_availability_operator(),
            list_bookings=operators.list_bookings_operator(),
            create_manual_booking=operators.create_manual_booking_operator(),
            cancel_booking=operators.cancel_booking_operator(),
            reschedule_booking=operators.reschedule_booking_operator(),
            update_booking_status=operators.update_booking_status_operator(),
            list_leads=operators.list_leads_operator(),
            update_lead_status=operators.update_lead_status_operator(),
            list_handoffs=operators.list_handoffs_operator(),
            resolve_handoff=operators.resolve_handoff_operator(),
            list_unanswered_questions=operators.list_unanswered_questions_operator(),
            answer_unanswered_question=operators.answer_unanswered_question_operator(),
            get_dashboard_stats=operators.get_dashboard_stats_operator(),
            start_calendar_connection=(
                operators.start_google_calendar_connection_operator()
            ),
            complete_calendar_connection=(
                operators.complete_google_calendar_connection_operator()
            ),
            disconnect_calendar=operators.disconnect_google_calendar_operator(),
        ),
        build_conversation_router(
            list_conversations_operator=operators.list_conversations_operator(),
            get_conversation_operator=operators.get_conversation_operator(),
            owner_test_chat_operator=operators.owner_test_chat_operator(),
            rate_conversation_operator=operators.rate_conversation_operator(),
            current_user=current_user,
        ),
        build_assistant_router(
            assemble_assistant_version_operator=(
                operators.assemble_assistant_version_operator()
            ),
            list_assistant_versions_operator=(
                operators.list_assistant_versions_operator()
            ),
            get_assistant_version_operator=operators.get_assistant_version_operator(),
            get_autotest_run_operator=operators.get_autotest_run_operator(),
            run_autotests_operator=operators.run_autotests_operator(),
            publish_assistant_version_operator=(
                operators.publish_assistant_version_operator()
            ),
            rollback_assistant_version_operator=(
                operators.rollback_assistant_version_operator()
            ),
            current_user=current_user,
        ),
        build_channel_router(
            telegram_webhook_operator=operators.telegram_webhook_operator(),
            meta_webhook_verification_operator=operators.verify_meta_webhook_operator(),
            meta_webhook_operator=operators.meta_webhook_operator(),
            platform_bot_webhook_operator=(
                operators.handle_platform_bot_update_operator()
            ),
            widget_config_operator=operators.get_widget_config_operator(),
            widget_message_operator=operators.widget_message_operator(),
        ),
        build_channel_settings_router(
            list_channels_operator=operators.list_channels_operator(),
            connect_channel_operator=operators.connect_channel_operator(),
            disable_channel_operator=operators.disable_channel_operator(),
            widget_snippet_operator=operators.get_widget_snippet_operator(),
            create_telegram_link_operator=operators.create_telegram_link_operator(),
            current_user=current_user,
        ),
        build_voice_router(
            voice_tool_operator=operators.voice_tool_webhook_operator(),
            call_initiation_operator=operators.start_voice_call_operator(),
            post_call_operator=operators.post_call_webhook_operator(),
        ),
        build_billing_router(
            get_billing_overview_operator=operators.get_billing_overview_operator(),
            start_trial_operator=operators.start_trial_operator(),
            change_plan_operator=operators.change_plan_operator(),
            cancel_subscription_operator=operators.cancel_subscription_operator(),
            start_checkout_operator=operators.start_checkout_operator(),
            payment_webhook_operator=operators.process_payment_webhook_operator(),
            current_user=current_user,
        ),
        build_admin_router(
            list_clients_operator=operators.list_clients_operator(),
            get_client_health_operator=operators.get_client_health_operator(),
            open_client_cabinet_operator=operators.open_client_cabinet_operator(),
            current_user=current_user,
        ),
        build_widget_script_router(),
    ]

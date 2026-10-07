"""Every HTTP router of the API, built from the container's operators."""

from fastapi import APIRouter

from app.containers.app import AppContainer
from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_client_router_assembly import build_admin_client_routers
from app.gateways.http.admin_ops_router_assembly import build_admin_ops_routers
from app.gateways.http.admin_routes import build_admin_router
from app.gateways.http.analytics_router_assembly import build_analytics_routers
from app.gateways.http.assistant_routes import build_assistant_router
from app.gateways.http.billing_router_assembly import build_billing_routers
from app.gateways.http.business_routes import build_business_router
from app.gateways.http.calendar_sync_router_assembly import build_calendar_sync_routers
from app.gateways.http.call_router_assembly import build_call_routers
from app.gateways.http.catalog_routes import build_catalog_router
from app.gateways.http.channel_setup_router_assembly import (
    build_channel_setup_routers,
)
from app.gateways.http.compliance_routes import build_compliance_router
from app.gateways.http.conversation_routes import build_conversation_router
from app.gateways.http.customers_router_assembly import build_customer_routers
from app.gateways.http.events_routes import build_events_router
from app.gateways.http.feedback_router_assembly import build_feedback_routers
from app.gateways.http.growth_router_assembly import build_growth_routers
from app.gateways.http.health_router_assembly import build_health_routers
from app.gateways.http.help_router_assembly import build_help_routers
from app.gateways.http.idempotency.idempotency_wiring import idempotency_of
from app.gateways.http.inbox_router_assembly import build_inbox_routers
from app.gateways.http.integration_router_assembly import build_integration_routers
from app.gateways.http.knowledge_routes import build_knowledge_router
from app.gateways.http.launch_router_assembly import build_launch_routers
from app.gateways.http.memory_router_assembly import build_memory_routers
from app.gateways.http.menu_import_routes import build_menu_import_router
from app.gateways.http.notification_routes import build_notification_router
from app.gateways.http.operations_router_assembly import build_operations_routers
from app.gateways.http.privacy_router_assembly import build_privacy_routers
from app.gateways.http.profile_routes import build_profile_router
from app.gateways.http.public_channel_router_assembly import (
    build_public_channel_router,
)
from app.gateways.http.public_site_router_assembly import build_public_site_routers
from app.gateways.http.referral_router_assembly import build_referral_routers
from app.gateways.http.resource_routes import build_resource_router
from app.gateways.http.security_router_assembly import build_security_routers
from app.gateways.http.sharing_router_assembly import build_sharing_routers
from app.gateways.http.spend_guard_router_assembly import build_spend_guard_routers
from app.gateways.http.teaching_router_assembly import build_teaching_routers
from app.gateways.http.user_authentication import (
    CurrentUserDependency,
    build_current_user_dependency,
)
from app.gateways.http.users_routes import build_users_router
from app.gateways.http.value_router_assembly import build_value_routers
from app.gateways.http.voice_routes import build_voice_router
from app.gateways.http.website_import_routes import build_website_import_router
from app.gateways.http.widget_error_routes import build_widget_error_router
from app.gateways.http.widget_script_routes import build_widget_script_router


def build_application_routers(app_container: AppContainer) -> list[APIRouter]:
    """
    Routers of every module, sharing one bearer-token dependency, the
    public channel routes (webhooks and the website widget) first.

    Operators are built once here; their use cases are stateless and the
    stateful collaborators (locks, caches, storage) are container singletons.
    """

    operators: OperatorsContainer = app_container.operators
    accounts = operators.accounts
    compliance = operators.compliance
    knowledge = operators.knowledge
    conversations = operators.conversations
    assistants = operators.assistants
    platform = operators.platform
    notifications = operators.notifications
    current_user: CurrentUserDependency = build_current_user_dependency(
        accounts.authenticate_user_operator(),
        app_container.utilities.session_assurance(),
        operators.spend_guard.admit_api_request_operator(),
    )
    business_access_operator = accounts.authorize_business_access_operator()
    return [
        # First: a request is matched against the routes one by one, and
        # widget polls (every open chat every 4 s) and webhook bursts are
        # most of the traffic; no other route answers these paths
        # (tests/platform/test_route_matching_order.py).
        build_public_channel_router(app_container),
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
        # Legal texts, the sub-processor list and the landing page's demos.
        *build_public_site_routers(operators),
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
        build_website_import_router(
            start_website_import_operator=knowledge.start_website_import_operator(),
            get_website_import_operator=knowledge.get_website_import_operator(),
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
        *build_operations_routers(app_container, current_user),
        build_events_router(
            current_user=current_user,
            authorize_business_access=business_access_operator,
            count_inbox_attention=app_container.operators.inbox.count_inbox_attention_operator(),
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
            list_conversation_messages_operator=(
                conversations.list_conversation_messages_operator()
            ),
            get_message_media_operator=conversations.get_message_media_operator(),
            idempotent=idempotency_of(operators, current_user),
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
        *build_channel_setup_routers(operators, current_user),
        build_voice_router(
            voice_tool_operator=conversations.voice_tool_webhook_operator(),
            call_initiation_operator=conversations.start_voice_call_operator(),
            post_call_operator=conversations.post_call_webhook_operator(),
        ),
        *build_billing_routers(operators, current_user),
        build_admin_router(
            list_clients_operator=platform.list_clients_operator(),
            get_client_health_operator=platform.get_client_health_operator(),
            open_client_cabinet_operator=platform.open_client_cabinet_operator(),
            current_user=current_user,
        ),
        build_notification_router(
            current_user=current_user,
            list_contacts=notifications.list_notification_contacts_operator(),
            check_contact=notifications.check_contact_operator(),
            get_settings=notifications.get_notification_settings_operator(),
            update_preferences=(
                notifications.update_notification_preferences_operator()
            ),
            subscribe_push=notifications.subscribe_push_operator(),
            unsubscribe_push=notifications.unsubscribe_push_operator(),
            check_device=notifications.check_device_operator(),
            resolve_link=notifications.resolve_staff_link_operator(),
        ),
        build_widget_script_router(),
        *build_health_routers(operators),
        build_widget_error_router(platform.report_widget_error_operator()),
        *build_launch_routers(operators, current_user),
        *build_call_routers(operators, current_user),
        *build_inbox_routers(operators, current_user),
        *build_sharing_routers(operators, current_user),
        *build_security_routers(operators, current_user),
        *build_value_routers(operators, current_user),
        *build_feedback_routers(operators, current_user),
        *build_privacy_routers(operators, current_user),
        *build_analytics_routers(operators, current_user),
        *build_admin_ops_routers(operators, current_user),
        *build_admin_client_routers(operators, current_user),
        *build_help_routers(operators, current_user),
        *build_teaching_routers(operators, current_user),
        *build_memory_routers(operators, current_user),
        *build_growth_routers(operators, current_user),
        *build_calendar_sync_routers(operators, current_user),
        *build_customer_routers(operators, current_user),
        *build_spend_guard_routers(operators, current_user),
        *build_referral_routers(operators, current_user),
        *build_integration_routers(operators, current_user),
    ]

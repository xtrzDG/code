"""The operations router (bookings, leads, handoffs, dashboard, Google Calendar)."""

from fastapi import APIRouter

from app.containers.app import AppContainer
from app.gateways.http.idempotency.idempotency_wiring import idempotency_of
from app.gateways.http.operations_routes import build_operations_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_operations_routers(
    app_container: AppContainer, current_user: CurrentUserDependency
) -> list[APIRouter]:
    """The operations routes, a manual booking idempotent by its key."""

    operators = app_container.operators
    operations = operators.operations
    return [
        build_operations_router(
            current_user=current_user,
            authorize_business_access=(
                operators.accounts.authorize_business_access_operator()
            ),
            check_availability=operations.check_availability_operator(),
            list_bookings=operations.list_bookings_operator(),
            create_manual_booking=operations.create_manual_booking_operator(),
            cancel_booking=operations.cancel_booking_operator(),
            reschedule_booking=operations.reschedule_booking_operator(),
            update_booking=operations.update_booking_operator(),
            revert_booking_status=operations.revert_booking_status_operator(),
            list_leads=operations.list_leads_operator(),
            update_lead_status=operations.update_lead_status_operator(),
            list_handoffs=operations.list_handoffs_operator(),
            resolve_handoff=operations.resolve_handoff_operator(),
            reopen_handoff=operations.reopen_handoff_operator(),
            list_unanswered_questions=operations.list_unanswered_questions_operator(),
            answer_unanswered_question=operations.answer_unanswered_question_operator(),
            get_dashboard_stats=operations.get_dashboard_stats_operator(),
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
            idempotent=idempotency_of(operators, current_user),
        )
    ]

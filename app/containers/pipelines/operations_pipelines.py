from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.operations_orchestrators import (
    OperationsOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class OperationsPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of bookings, leads, handoffs, unanswered questions, the
    dashboard, Google Calendar and the booking reminders job.
    """

    operations_orchestrators: OperationsOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_pipeline = orchestrator_pipeline(
        operations_orchestrators.check_availability_orchestrator
    )
    list_bookings_pipeline = orchestrator_pipeline(
        operations_orchestrators.list_bookings_orchestrator
    )
    create_manual_booking_pipeline = orchestrator_pipeline(
        operations_orchestrators.create_manual_booking_orchestrator
    )
    cancel_booking_pipeline = orchestrator_pipeline(
        operations_orchestrators.cancel_booking_orchestrator
    )
    reschedule_booking_pipeline = orchestrator_pipeline(
        operations_orchestrators.reschedule_booking_orchestrator
    )
    update_booking_pipeline = orchestrator_pipeline(
        operations_orchestrators.update_booking_orchestrator
    )
    list_leads_pipeline = orchestrator_pipeline(
        operations_orchestrators.list_leads_orchestrator
    )
    update_lead_status_pipeline = orchestrator_pipeline(
        operations_orchestrators.update_lead_status_orchestrator
    )
    list_handoffs_pipeline = orchestrator_pipeline(
        operations_orchestrators.list_handoffs_orchestrator
    )
    resolve_handoff_pipeline = orchestrator_pipeline(
        operations_orchestrators.resolve_handoff_orchestrator
    )
    list_unanswered_questions_pipeline = orchestrator_pipeline(
        operations_orchestrators.list_unanswered_questions_orchestrator
    )
    answer_unanswered_question_pipeline = orchestrator_pipeline(
        operations_orchestrators.answer_unanswered_question_orchestrator
    )
    get_dashboard_stats_pipeline = orchestrator_pipeline(
        operations_orchestrators.get_dashboard_stats_orchestrator
    )
    start_google_calendar_connection_pipeline = orchestrator_pipeline(
        operations_orchestrators.start_google_calendar_connection_orchestrator
    )
    complete_google_calendar_connection_pipeline = orchestrator_pipeline(
        operations_orchestrators.complete_google_calendar_connection_orchestrator
    )
    disconnect_google_calendar_pipeline = orchestrator_pipeline(
        operations_orchestrators.disconnect_google_calendar_orchestrator
    )
    get_google_calendar_connection_pipeline = orchestrator_pipeline(
        operations_orchestrators.get_google_calendar_connection_orchestrator
    )

    # --- Periodic job of the background worker.
    send_booking_reminders_pipeline = orchestrator_pipeline(
        operations_orchestrators.send_booking_reminders_orchestrator
    )

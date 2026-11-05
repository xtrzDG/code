from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.scheduling_use_cases import SchedulingUseCasesContainer


class OperationsOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of bookings, leads, handoffs, unanswered questions,
    the dashboard, Google Calendar and the booking reminders job.
    """

    scheduling_use_cases: SchedulingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    booking_use_cases: BookingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    follow_up_use_cases: FollowUpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_orchestrator = use_case_orchestrator(
        booking_use_cases.check_availability_use_case
    )
    list_bookings_orchestrator = use_case_orchestrator(
        booking_use_cases.list_bookings_use_case
    )
    get_booking_grid_orchestrator = use_case_orchestrator(
        scheduling_use_cases.get_booking_grid_use_case
    )
    create_manual_booking_orchestrator = use_case_orchestrator(
        booking_use_cases.create_manual_booking_use_case
    )
    cancel_booking_orchestrator = use_case_orchestrator(
        booking_use_cases.cancel_booking_use_case
    )
    reschedule_booking_orchestrator = use_case_orchestrator(
        booking_use_cases.reschedule_booking_use_case
    )
    update_booking_orchestrator = use_case_orchestrator(
        booking_use_cases.update_booking_use_case
    )
    revert_booking_status_orchestrator = use_case_orchestrator(
        booking_use_cases.revert_booking_status_use_case
    )
    list_leads_orchestrator = use_case_orchestrator(
        follow_up_use_cases.list_leads_use_case
    )
    update_lead_status_orchestrator = use_case_orchestrator(
        follow_up_use_cases.update_lead_status_use_case
    )
    list_handoffs_orchestrator = use_case_orchestrator(
        follow_up_use_cases.list_handoffs_use_case
    )
    resolve_handoff_orchestrator = use_case_orchestrator(
        follow_up_use_cases.resolve_handoff_use_case
    )
    reopen_handoff_orchestrator = use_case_orchestrator(
        follow_up_use_cases.reopen_handoff_use_case
    )
    list_unanswered_questions_orchestrator = use_case_orchestrator(
        follow_up_use_cases.list_unanswered_questions_use_case
    )
    answer_unanswered_question_orchestrator = use_case_orchestrator(
        follow_up_use_cases.answer_unanswered_question_use_case
    )
    get_dashboard_stats_orchestrator = use_case_orchestrator(
        follow_up_use_cases.get_dashboard_stats_use_case
    )
    start_google_calendar_connection_orchestrator = use_case_orchestrator(
        scheduling_use_cases.start_google_calendar_connection_use_case
    )
    complete_google_calendar_connection_orchestrator = use_case_orchestrator(
        scheduling_use_cases.complete_google_calendar_connection_use_case
    )
    disconnect_google_calendar_orchestrator = use_case_orchestrator(
        scheduling_use_cases.disconnect_google_calendar_use_case
    )
    get_google_calendar_connection_orchestrator = use_case_orchestrator(
        scheduling_use_cases.get_google_calendar_connection_use_case
    )

    # --- Periodic job of the background worker.
    send_booking_reminders_orchestrator = use_case_orchestrator(
        booking_use_cases.send_booking_reminders_use_case
    )

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.operations_pipelines import OperationsPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class OperationsOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of bookings, leads, handoffs, unanswered questions, the
    dashboard, Google Calendar and the booking reminders job.
    """

    operations_pipelines: OperationsPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve;
    # platform_pipeline_operator marks platform-level work (platform-wide).
    storage_scope = utilities.storage_scope

    # --- Bookings, leads, handoffs, questions, dashboard, Google Calendar.
    check_availability_operator = pipeline_operator(
        operations_pipelines.check_availability_pipeline, storage_scope
    )
    list_bookings_operator = pipeline_operator(
        operations_pipelines.list_bookings_pipeline, storage_scope
    )
    create_manual_booking_operator = pipeline_operator(
        operations_pipelines.create_manual_booking_pipeline, storage_scope
    )
    cancel_booking_operator = pipeline_operator(
        operations_pipelines.cancel_booking_pipeline, storage_scope
    )
    reschedule_booking_operator = pipeline_operator(
        operations_pipelines.reschedule_booking_pipeline, storage_scope
    )
    update_booking_operator = pipeline_operator(
        operations_pipelines.update_booking_pipeline, storage_scope
    )
    list_leads_operator = pipeline_operator(
        operations_pipelines.list_leads_pipeline, storage_scope
    )
    update_lead_status_operator = pipeline_operator(
        operations_pipelines.update_lead_status_pipeline, storage_scope
    )
    list_handoffs_operator = pipeline_operator(
        operations_pipelines.list_handoffs_pipeline, storage_scope
    )
    resolve_handoff_operator = pipeline_operator(
        operations_pipelines.resolve_handoff_pipeline, storage_scope
    )
    list_unanswered_questions_operator = pipeline_operator(
        operations_pipelines.list_unanswered_questions_pipeline, storage_scope
    )
    answer_unanswered_question_operator = pipeline_operator(
        operations_pipelines.answer_unanswered_question_pipeline, storage_scope
    )
    get_dashboard_stats_operator = pipeline_operator(
        operations_pipelines.get_dashboard_stats_pipeline, storage_scope
    )
    get_inbox_counts_operator = pipeline_operator(
        operations_pipelines.get_inbox_counts_pipeline, storage_scope
    )
    get_attention_counts_operator = pipeline_operator(
        operations_pipelines.get_attention_counts_pipeline, storage_scope
    )
    start_google_calendar_connection_operator = pipeline_operator(
        operations_pipelines.start_google_calendar_connection_pipeline, storage_scope
    )
    # The business is known only from the consent state (read across
    # businesses); the use case checks it is the signed-in owner's.
    complete_google_calendar_connection_operator = platform_pipeline_operator(
        operations_pipelines.complete_google_calendar_connection_pipeline, storage_scope
    )
    disconnect_google_calendar_operator = pipeline_operator(
        operations_pipelines.disconnect_google_calendar_pipeline, storage_scope
    )
    get_google_calendar_connection_operator = pipeline_operator(
        operations_pipelines.get_google_calendar_connection_pipeline, storage_scope
    )

    # --- Periodic job of the background worker.
    send_booking_reminders_operator = platform_pipeline_operator(
        operations_pipelines.send_booking_reminders_pipeline, storage_scope
    )

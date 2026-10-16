from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.calendar_sync_use_cases import (
    CalendarSyncUseCasesContainer,
)


class CalendarSyncOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of two-way availability (1160): one use case each."""

    calendar_use_cases: CalendarSyncUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_resource_calendar_orchestrator = use_case_orchestrator(
        calendar_use_cases.get_resource_calendar_use_case
    )
    sync_resource_calendar_orchestrator = use_case_orchestrator(
        calendar_use_cases.sync_resource_calendar_use_case
    )
    link_google_calendar_orchestrator = use_case_orchestrator(
        calendar_use_cases.link_google_calendar_use_case
    )
    add_ical_import_orchestrator = use_case_orchestrator(
        calendar_use_cases.add_ical_import_use_case
    )
    link_booking_system_orchestrator = use_case_orchestrator(
        calendar_use_cases.link_booking_system_use_case
    )
    remove_calendar_source_orchestrator = use_case_orchestrator(
        calendar_use_cases.remove_calendar_source_use_case
    )
    create_ical_export_orchestrator = use_case_orchestrator(
        calendar_use_cases.create_ical_export_use_case
    )
    remove_ical_export_orchestrator = use_case_orchestrator(
        calendar_use_cases.remove_ical_export_use_case
    )
    list_google_calendars_orchestrator = use_case_orchestrator(
        calendar_use_cases.list_google_calendars_use_case
    )
    list_integrations_orchestrator = use_case_orchestrator(
        calendar_use_cases.list_integrations_use_case
    )
    sync_due_calendars_orchestrator = use_case_orchestrator(
        calendar_use_cases.sync_due_calendars_use_case
    )
    export_resource_busy_times_orchestrator = use_case_orchestrator(
        calendar_use_cases.export_resource_busy_times_use_case
    )
    write_booking_system_booking_orchestrator = use_case_orchestrator(
        calendar_use_cases.write_booking_system_booking_use_case
    )

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.calendar_sync_orchestrators import (
    CalendarSyncOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class CalendarSyncPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of two-way availability (1160)."""

    calendars: CalendarSyncOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_resource_calendar_pipeline = orchestrator_pipeline(
        calendars.get_resource_calendar_orchestrator
    )
    sync_resource_calendar_pipeline = orchestrator_pipeline(
        calendars.sync_resource_calendar_orchestrator
    )
    link_google_calendar_pipeline = orchestrator_pipeline(
        calendars.link_google_calendar_orchestrator
    )
    add_ical_import_pipeline = orchestrator_pipeline(
        calendars.add_ical_import_orchestrator
    )
    link_booking_system_pipeline = orchestrator_pipeline(
        calendars.link_booking_system_orchestrator
    )
    remove_calendar_source_pipeline = orchestrator_pipeline(
        calendars.remove_calendar_source_orchestrator
    )
    create_ical_export_pipeline = orchestrator_pipeline(
        calendars.create_ical_export_orchestrator
    )
    remove_ical_export_pipeline = orchestrator_pipeline(
        calendars.remove_ical_export_orchestrator
    )
    list_google_calendars_pipeline = orchestrator_pipeline(
        calendars.list_google_calendars_orchestrator
    )
    list_integrations_pipeline = orchestrator_pipeline(
        calendars.list_integrations_orchestrator
    )
    sync_due_calendars_pipeline = orchestrator_pipeline(
        calendars.sync_due_calendars_orchestrator
    )
    export_resource_busy_times_pipeline = orchestrator_pipeline(
        calendars.export_resource_busy_times_orchestrator
    )

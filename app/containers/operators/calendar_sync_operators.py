from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.calendar_sync_pipelines import (
    CalendarSyncPipelinesContainer,
)
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class CalendarSyncOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of two-way availability: the cabinet's endpoints in their
    business's scope; the sync job over every business (platform-wide);
    the public export feed, whose address names no business, unscoped (its
    use case finds the feed explicitly across businesses, then enters the
    feed's business).
    """

    calendar_pipelines: CalendarSyncPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_resource_calendar_operator = pipeline_operator(
        calendar_pipelines.get_resource_calendar_pipeline, storage_scope
    )
    sync_resource_calendar_operator = pipeline_operator(
        calendar_pipelines.sync_resource_calendar_pipeline, storage_scope
    )
    link_google_calendar_operator = pipeline_operator(
        calendar_pipelines.link_google_calendar_pipeline, storage_scope
    )
    add_ical_import_operator = pipeline_operator(
        calendar_pipelines.add_ical_import_pipeline, storage_scope
    )
    link_booking_system_operator = pipeline_operator(
        calendar_pipelines.link_booking_system_pipeline, storage_scope
    )
    remove_calendar_source_operator = pipeline_operator(
        calendar_pipelines.remove_calendar_source_pipeline, storage_scope
    )
    create_ical_export_operator = pipeline_operator(
        calendar_pipelines.create_ical_export_pipeline, storage_scope
    )
    remove_ical_export_operator = pipeline_operator(
        calendar_pipelines.remove_ical_export_pipeline, storage_scope
    )
    list_google_calendars_operator = pipeline_operator(
        calendar_pipelines.list_google_calendars_pipeline, storage_scope
    )
    list_integrations_operator = pipeline_operator(
        calendar_pipelines.list_integrations_pipeline, storage_scope
    )
    sync_due_calendars_operator = platform_pipeline_operator(
        calendar_pipelines.sync_due_calendars_pipeline, storage_scope
    )
    export_resource_busy_times_operator = pipeline_operator(
        calendar_pipelines.export_resource_busy_times_pipeline, storage_scope
    )
    # The `write_booking_system_booking` job, in its booking's business.
    write_booking_system_booking_operator = pipeline_operator(
        calendar_pipelines.write_booking_system_booking_pipeline, storage_scope
    )

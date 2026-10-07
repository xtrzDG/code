from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calendar_sync.busy_reads import GoogleCalendarList
from app.schemas.dto.calendar_sync.calendar_commands import (
    AddIcalImportCommand,
    BusinessCalendarsQuery,
    IcalExportCommand,
    LinkBookingSystemCommand,
    LinkGoogleCalendarCommand,
    RemoveCalendarSourceCommand,
    ResourceCalendarQuery,
    SyncResourceCalendarCommand,
)
from app.schemas.dto.calendar_sync.ical_export import IcalExportFile, IcalExportRequest
from app.schemas.dto.calendar_sync.integrations import IntegrationList
from app.schemas.dto.calendar_sync.resource_calendar import (
    IcalExportCreated,
    ResourceCalendarView,
)
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.use_cases.calendar_sync.add_ical_import_use_case import AddIcalImportUseCase
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges
from app.use_cases.calendar_sync.create_ical_export_use_case import (
    CreateIcalExportUseCase,
)
from app.use_cases.calendar_sync.export_resource_busy_times_use_case import (
    ExportResourceBusyTimesUseCase,
)
from app.use_cases.calendar_sync.get_resource_calendar_use_case import (
    GetResourceCalendarUseCase,
)
from app.use_cases.calendar_sync.link_booking_system_use_case import (
    LinkBookingSystemUseCase,
)
from app.use_cases.calendar_sync.link_google_calendar_use_case import (
    LinkGoogleCalendarUseCase,
)
from app.use_cases.calendar_sync.list_google_calendars_use_case import (
    ListGoogleCalendarsUseCase,
)
from app.use_cases.calendar_sync.list_integrations_use_case import (
    ListIntegrationsUseCase,
)
from app.use_cases.calendar_sync.remove_calendar_source_use_case import (
    RemoveCalendarSourceUseCase,
)
from app.use_cases.calendar_sync.remove_ical_export_use_case import (
    RemoveIcalExportUseCase,
)
from app.use_cases.calendar_sync.resource_calendar_reader import (
    ResourceCalendarReader,
)
from app.use_cases.calendar_sync.sync_due_calendars_use_case import (
    SyncDueCalendarsUseCase,
)
from app.use_cases.calendar_sync.sync_resource_calendar_use_case import (
    SyncResourceCalendarUseCase,
)
from app.use_cases.calendar_sync.write_booking_system_booking_use_case import (
    WriteBookingSystemBookingUseCase,
)


class CalendarSyncUseCasesContainer(containers.DeclarativeContainer):
    """
    Two-way availability (1160): a resource's calendars in the cabinet
    (Google calendar, iCal imports, Cal.com, the export address, "Sync
    now"), Settings → Integrations, the five-minute sync job and the public
    export feed.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    reader: Factory[ResourceCalendarReader] = Factory(
        ResourceCalendarReader,
        resource_repo=repositories.resource_repo,
        link_repo=repositories.resource_calendar_link_repo,
        busy_times_repo=repositories.calendar_busy_times_repo,
        export_feed_repo=repositories.ical_export_feed_repo,
        connection_repo=repositories.calendar_connection_repo,
        calendar_client=clients.google_calendar_client,
        connectors=facilitators.booking_system_connectors,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    changes: Factory[CalendarChanges] = Factory(
        CalendarChanges,
        reader=reader,
        busy_time_sync=facilitators.busy_time_sync,
        audit_log_repo=repositories.audit_log_repo,
    )

    get_resource_calendar_use_case: Factory[
        UseCaseContract[ResourceCalendarQuery, ResourceCalendarView]
    ] = Factory(GetResourceCalendarUseCase, reader=reader)
    sync_resource_calendar_use_case: Factory[
        UseCaseContract[SyncResourceCalendarCommand, ResourceCalendarView]
    ] = Factory(SyncResourceCalendarUseCase, changes=changes)
    link_google_calendar_use_case: Factory[
        UseCaseContract[LinkGoogleCalendarCommand, ResourceCalendarView]
    ] = Factory(LinkGoogleCalendarUseCase, changes=changes)
    add_ical_import_use_case: Factory[
        UseCaseContract[AddIcalImportCommand, ResourceCalendarView]
    ] = Factory(
        AddIcalImportUseCase, changes=changes, secret_cipher=adapters.secret_cipher
    )
    link_booking_system_use_case: Factory[
        UseCaseContract[LinkBookingSystemCommand, ResourceCalendarView]
    ] = Factory(
        LinkBookingSystemUseCase, changes=changes, secret_cipher=adapters.secret_cipher
    )
    remove_calendar_source_use_case: Factory[
        UseCaseContract[RemoveCalendarSourceCommand, None]
    ] = Factory(RemoveCalendarSourceUseCase, changes=changes)
    create_ical_export_use_case: Factory[
        UseCaseContract[IcalExportCommand, IcalExportCreated]
    ] = Factory(
        CreateIcalExportUseCase,
        changes=changes,
        app_base_url=config.app_settings.provided.app_base_url,
    )
    remove_ical_export_use_case: Factory[UseCaseContract[IcalExportCommand, None]] = (
        Factory(RemoveIcalExportUseCase, changes=changes)
    )
    list_google_calendars_use_case: Factory[
        UseCaseContract[BusinessCalendarsQuery, GoogleCalendarList]
    ] = Factory(ListGoogleCalendarsUseCase, busy_time_sync=facilitators.busy_time_sync)
    list_integrations_use_case: Factory[
        UseCaseContract[BusinessCalendarsQuery, IntegrationList]
    ] = Factory(
        ListIntegrationsUseCase,
        link_repo=repositories.resource_calendar_link_repo,
        export_feed_repo=repositories.ical_export_feed_repo,
        connection_repo=repositories.calendar_connection_repo,
        calendar_client=clients.google_calendar_client,
    )
    sync_due_calendars_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        SyncDueCalendarsUseCase,
        link_repo=repositories.resource_calendar_link_repo,
        resource_repo=repositories.resource_repo,
        busy_time_sync=facilitators.busy_time_sync,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    export_resource_busy_times_use_case: Factory[
        UseCaseContract[IcalExportRequest, IcalExportFile]
    ] = Factory(
        ExportResourceBusyTimesUseCase,
        export_feed_repo=repositories.ical_export_feed_repo,
        business_repo=repositories.business_repo,
        resource_repo=repositories.resource_repo,
        booking_repo=repositories.booking_repo,
        busy_times_repo=repositories.calendar_busy_times_repo,
        text_resolver=utilities.localized_text_resolver,
        rate_limits=registries.request_rate_limit_registry,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The queued write of a booking to its resource's booking system.
    write_booking_system_booking_use_case: Factory[
        UseCaseContract[QueuedJobInput, JobReport]
    ] = Factory(
        WriteBookingSystemBookingUseCase,
        booking_repo=repositories.booking_repo,
        link_repo=repositories.resource_calendar_link_repo,
        contact_repo=repositories.contact_repo,
        business_repo=repositories.business_repo,
        connectors=facilitators.booking_system_connectors,
        secret_cipher=adapters.secret_cipher,
        text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
    )

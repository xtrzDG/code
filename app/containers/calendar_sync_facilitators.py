from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, List, Singleton

from app.adapters.booking_systems.cal_com_booking_system_adapter import (
    CalComBookingSystemAdapter,
)
from app.clients.cal_com.cal_com_client import CalComClient
from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.facilitators.calendar.google_calendar_sync_facilitator import (
    GoogleCalendarSyncFacilitator,
)
from app.facilitators.calendar_sync.booking_system_busy_reader import (
    BookingSystemBusyReader,
)
from app.facilitators.calendar_sync.busy_time_sync_facilitator import (
    BusyTimeSyncFacilitator,
)
from app.facilitators.calendar_sync.google_busy_reader import GoogleBusyReader
from app.facilitators.calendar_sync.ical_busy_reader import IcalBusyReader
from app.registries.booking_systems.booking_system_connector_registry import (
    BookingSystemConnectorRegistry,
)


class CalendarSyncFacilitatorsContainer(containers.DeclarativeContainer):
    """
    The calendars on both sides of a booking: bookings mirrored into the
    business's Google Calendar, and the busy times of the calendars outside
    the platform that block resources (Google free/busy, iCal feeds, the
    booking systems behind their connector registry: Cal.com). A child of
    FacilitatorsContainer, which names its facilitators flat
    (`facilitators.calendar_sync_facilitator`, `facilitators.busy_time_sync`).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    calendar_sync_facilitator: Singleton[GoogleCalendarSyncFacilitator] = Singleton(
        GoogleCalendarSyncFacilitator,
        connection_repo=repositories.calendar_connection_repo,
        event_link_repo=repositories.calendar_event_link_repo,
        business_repo=repositories.business_repo,
        resource_repo=repositories.resource_repo,
        contact_repo=repositories.contact_repo,
        calendar_client=clients.google_calendar_client,
        secret_cipher=adapters.secret_cipher,
        phone_number_parser=utilities.phone_number_parser,
        event_text_transformer=transformers.calendar_event_text_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The booking systems the platform speaks to, one connector each.
    cal_com_client: Singleton[CalComClient] = Singleton(CalComClient)
    booking_system_connectors: Singleton[BookingSystemConnectorRegistry] = Singleton(
        BookingSystemConnectorRegistry,
        connectors=List(Singleton(CalComBookingSystemAdapter, client=cal_com_client)),
    )
    # Imported iCal feeds, read through the safe fetcher.
    ical_reader: Singleton[IcalBusyReader] = Singleton(
        IcalBusyReader,
        fetcher=clients.safe_http_fetcher,
        secret_cipher=adapters.secret_cipher,
    )
    busy_time_sync: Singleton[BusyTimeSyncFacilitator] = Singleton(
        BusyTimeSyncFacilitator,
        link_repo=repositories.resource_calendar_link_repo,
        busy_times_repo=repositories.calendar_busy_times_repo,
        resource_repo=repositories.resource_repo,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        google=Singleton(
            GoogleBusyReader,
            connection_repo=repositories.calendar_connection_repo,
            calendar_client=clients.google_calendar_client,
            secret_cipher=adapters.secret_cipher,
            booking_repo=repositories.booking_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
        ical=ical_reader,
        booking_systems=Singleton(
            BookingSystemBusyReader,
            registry=booking_system_connectors,
            secret_cipher=adapters.secret_cipher,
        ),
        wall_clock=time_provider.microsecond_wall_clock,
    )

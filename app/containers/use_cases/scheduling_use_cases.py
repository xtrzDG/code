from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.booking_grid import BookingGrid, BookingGridQuery
from app.schemas.dto.calendar import (
    CalendarConnectionOutcome,
    CalendarConnectionStatusQuery,
    CalendarConnectionStatusView,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarConnectUrlView,
    CalendarDisconnectResult,
    CompleteCalendarConnectionCommand,
    DisconnectCalendarCommand,
    StartCalendarConnectionCommand,
)
from app.schemas.dto.resources import (
    CreateResourceCommand,
    CreateScheduleExceptionCommand,
    DeleteScheduleExceptionCommand,
    ResourceList,
    ResourceListQuery,
    ResourceView,
    ScheduleExceptionDeletion,
    ScheduleExceptionList,
    ScheduleExceptionListQuery,
    ScheduleExceptionView,
    UpdateResourceCommand,
)
from app.use_cases.bookings.calendar.get_booking_grid_use_case import (
    GetBookingGridUseCase,
)
from app.use_cases.calendar.complete_google_calendar_connection_use_case import (
    CompleteGoogleCalendarConnectionUseCase,
)
from app.use_cases.calendar.disconnect_google_calendar_use_case import (
    DisconnectGoogleCalendarUseCase,
)
from app.use_cases.calendar.get_google_calendar_connection_use_case import (
    GetGoogleCalendarConnectionUseCase,
)
from app.use_cases.calendar.start_google_calendar_connection_use_case import (
    StartGoogleCalendarConnectionUseCase,
)
from app.use_cases.resources.create_resource_use_case import CreateResourceUseCase
from app.use_cases.resources.create_schedule_exception_use_case import (
    CreateScheduleExceptionUseCase,
)
from app.use_cases.resources.delete_schedule_exception_use_case import (
    DeleteScheduleExceptionUseCase,
)
from app.use_cases.resources.list_resources_use_case import ListResourcesUseCase
from app.use_cases.resources.list_schedule_exceptions_use_case import (
    ListScheduleExceptionsUseCase,
)
from app.use_cases.resources.update_resource_use_case import UpdateResourceUseCase


class SchedulingUseCasesContainer(containers.DeclarativeContainer):
    """
    What bookings are placed on: resources, their schedule exceptions, the
    bookings calendar over them and the Google Calendar connection.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Resources, schedules and exceptions.
    create_resource_use_case: Factory[
        UseCaseContract[CreateResourceCommand, ResourceView]
    ] = Factory(
        CreateResourceUseCase,
        business_repo=repositories.business_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_resource_use_case: Factory[
        UseCaseContract[UpdateResourceCommand, ResourceView]
    ] = Factory(
        UpdateResourceUseCase,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_resources_use_case: Factory[
        UseCaseContract[ResourceListQuery, ResourceList]
    ] = Factory(
        ListResourcesUseCase,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    create_schedule_exception_use_case: Factory[
        UseCaseContract[CreateScheduleExceptionCommand, ScheduleExceptionView]
    ] = Factory(
        CreateScheduleExceptionUseCase,
        business_repo=repositories.business_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_schedule_exceptions_use_case: Factory[
        UseCaseContract[ScheduleExceptionListQuery, ScheduleExceptionList]
    ] = Factory(
        ListScheduleExceptionsUseCase,
        schedule_exception_repo=repositories.schedule_exception_repo,
    )
    delete_schedule_exception_use_case: Factory[
        UseCaseContract[DeleteScheduleExceptionCommand, ScheduleExceptionDeletion]
    ] = Factory(
        DeleteScheduleExceptionUseCase,
        schedule_exception_repo=repositories.schedule_exception_repo,
    )

    # --- The bookings calendar (Bookings → Day, Week, Nights).
    get_booking_grid_use_case: Factory[
        UseCaseContract[BookingGridQuery, BookingGrid]
    ] = Factory(
        GetBookingGridUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Google Calendar.
    start_google_calendar_connection_use_case: Factory[
        UseCaseContract[StartCalendarConnectionCommand, CalendarConnectUrlView]
    ] = Factory(
        StartGoogleCalendarConnectionUseCase,
        business_repo=repositories.business_repo,
        authorization_state_repo=repositories.calendar_authorization_state_repo,
        calendar_client=clients.google_calendar_client,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    complete_google_calendar_connection_use_case: Factory[
        UseCaseContract[CompleteCalendarConnectionCommand, CalendarConnectionOutcome]
    ] = Factory(
        CompleteGoogleCalendarConnectionUseCase,
        authorization_state_repo=repositories.calendar_authorization_state_repo,
        connection_repo=repositories.calendar_connection_repo,
        calendar_client=clients.google_calendar_client,
        secret_cipher=adapters.secret_cipher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    disconnect_google_calendar_use_case: Factory[
        UseCaseContract[DisconnectCalendarCommand, CalendarDisconnectResult]
    ] = Factory(
        DisconnectGoogleCalendarUseCase,
        connection_repo=repositories.calendar_connection_repo,
        event_link_repo=repositories.calendar_event_link_repo,
        calendar_client=clients.google_calendar_client,
        secret_cipher=adapters.secret_cipher,
    )
    get_google_calendar_connection_use_case: Factory[
        UseCaseContract[CalendarConnectionStatusQuery, CalendarConnectionStatusView]
    ] = Factory(
        GetGoogleCalendarConnectionUseCase,
        connection_repo=repositories.calendar_connection_repo,
        calendar_client=clients.google_calendar_client,
    )

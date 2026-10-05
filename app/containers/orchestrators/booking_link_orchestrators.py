from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.use_cases.booking_link_use_cases import (
    BookingLinkUseCasesContainer,
)
from app.containers.utilities import UtilitiesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.bookings.managed_booking_orchestrator import (
    ManagedBookingOrchestrator,
)
from app.schemas.dto.booking_manage import (
    BookingCalendarFile,
    ManagedBookingRequest,
    ManagedBookingSlots,
    ManagedBookingView,
)

type ManagedBookingOrchestration[Output] = Factory[
    OrchestratorContract[ManagedBookingRequest, Output]
]


class BookingLinkOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of a guest's booking page: each checks the link, then
    runs its use case in the scope of the business the link names.
    """

    booking_link_use_cases: BookingLinkUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    managed_booking_orchestrator: ManagedBookingOrchestration[ManagedBookingView] = (
        Factory(
            ManagedBookingOrchestrator[ManagedBookingView],
            open_link=booking_link_use_cases.open_booking_manage_link_use_case,
            act=booking_link_use_cases.get_managed_booking_use_case,
            storage_scope=utilities.storage_scope,
        )
    )
    managed_booking_calendar_orchestrator: ManagedBookingOrchestration[
        BookingCalendarFile
    ] = Factory(
        ManagedBookingOrchestrator[BookingCalendarFile],
        open_link=booking_link_use_cases.open_booking_manage_link_use_case,
        act=booking_link_use_cases.get_managed_booking_calendar_use_case,
        storage_scope=utilities.storage_scope,
    )
    managed_booking_slots_orchestrator: ManagedBookingOrchestration[
        ManagedBookingSlots
    ] = Factory(
        ManagedBookingOrchestrator[ManagedBookingSlots],
        open_link=booking_link_use_cases.open_booking_manage_link_use_case,
        act=booking_link_use_cases.find_managed_booking_slots_use_case,
        storage_scope=utilities.storage_scope,
    )
    cancel_managed_booking_orchestrator: ManagedBookingOrchestration[
        ManagedBookingView
    ] = Factory(
        ManagedBookingOrchestrator[ManagedBookingView],
        open_link=booking_link_use_cases.open_booking_manage_link_use_case,
        act=booking_link_use_cases.cancel_managed_booking_use_case,
        storage_scope=utilities.storage_scope,
    )
    reschedule_managed_booking_orchestrator: ManagedBookingOrchestration[
        ManagedBookingView
    ] = Factory(
        ManagedBookingOrchestrator[ManagedBookingView],
        open_link=booking_link_use_cases.open_booking_manage_link_use_case,
        act=booking_link_use_cases.reschedule_managed_booking_use_case,
        storage_scope=utilities.storage_scope,
    )

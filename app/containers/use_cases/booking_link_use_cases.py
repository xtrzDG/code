from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.booking_manage import (
    BookingCalendarFile,
    BookingManageClaims,
    ManagedBookingAction,
    ManagedBookingSlots,
    ManagedBookingView,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.use_cases.bookings.public.cancel_managed_booking_use_case import (
    CancelManagedBookingUseCase,
)
from app.use_cases.bookings.public.find_managed_booking_slots_use_case import (
    FindManagedBookingSlotsUseCase,
)
from app.use_cases.bookings.public.get_managed_booking_calendar_use_case import (
    GetManagedBookingCalendarUseCase,
)
from app.use_cases.bookings.public.get_managed_booking_use_case import (
    GetManagedBookingUseCase,
)
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from app.use_cases.bookings.public.open_booking_manage_link_use_case import (
    OpenBookingManageLinkUseCase,
)
from app.use_cases.bookings.public.reschedule_managed_booking_use_case import (
    RescheduleManagedBookingUseCase,
)

type ManagedBookingUseCase[Output] = Factory[
    UseCaseContract[ManagedBookingAction, Output]
]


class BookingLinkUseCasesContainer(containers.DeclarativeContainer):
    """
    A guest's booking page behind its manage link (/r/{token}): opening the
    link, the page, its calendar file, free times, cancelling and moving.
    Changes run through the booking use cases a chat customer's do.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    booking_use_cases: BookingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    managed_booking_pages: Factory[ManagedBookingPages] = Factory(
        ManagedBookingPages,
        guest_bookings=booking_use_cases.guest_booking_reader,
        channel_repo=repositories.channel_repo,
        link_signer=utilities.booking_manage_token_signer,
        rate_limits=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        cabinet_base_url=config.app_settings.provided.cabinet_base_url,
    )
    open_booking_manage_link_use_case: Factory[
        UseCaseContract[BookingManageToken, BookingManageClaims]
    ] = Factory(
        OpenBookingManageLinkUseCase,
        link_signer=utilities.booking_manage_token_signer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_managed_booking_use_case: ManagedBookingUseCase[ManagedBookingView] = Factory(
        GetManagedBookingUseCase, pages=managed_booking_pages
    )
    get_managed_booking_calendar_use_case: ManagedBookingUseCase[
        BookingCalendarFile
    ] = Factory(
        GetManagedBookingCalendarUseCase,
        pages=managed_booking_pages,
        text_resolver=utilities.localized_text_resolver,
        cabinet_base_url=config.app_settings.provided.cabinet_base_url,
    )
    find_managed_booking_slots_use_case: ManagedBookingUseCase[ManagedBookingSlots] = (
        Factory(
            FindManagedBookingSlotsUseCase,
            pages=managed_booking_pages,
            check_availability=booking_use_cases.check_availability_use_case,
        )
    )
    cancel_managed_booking_use_case: ManagedBookingUseCase[ManagedBookingView] = (
        Factory(
            CancelManagedBookingUseCase,
            pages=managed_booking_pages,
            cancel_booking=booking_use_cases.cancel_booking_use_case,
        )
    )
    reschedule_managed_booking_use_case: ManagedBookingUseCase[ManagedBookingView] = (
        Factory(
            RescheduleManagedBookingUseCase,
            pages=managed_booking_pages,
            reschedule_booking=booking_use_cases.reschedule_booking_use_case,
            send_confirmation=booking_use_cases.send_booking_confirmation_use_case,
        )
    )

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    BookingView,
    CancelBookingCommand,
    CreateBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.dto.jobs import (
    JobReport,
    JobTick,
)
from app.schemas.dto.operations.bookings import (
    BookingPage,
    ListBookingsQuery,
    ManualBookingCommand,
    UpdateBookingCommand,
)
from app.use_cases.bookings.cancel_booking_use_case import CancelBookingUseCase
from app.use_cases.bookings.check_availability_use_case import CheckAvailabilityUseCase
from app.use_cases.bookings.create_booking_use_case import CreateBookingUseCase
from app.use_cases.bookings.list_bookings_use_case import ListBookingsUseCase
from app.use_cases.bookings.manual_booking.create_manual_booking_use_case import (
    CreateManualBookingUseCase,
)
from app.use_cases.bookings.reminders.send_booking_reminders_use_case import (
    SendBookingRemindersUseCase,
)
from app.use_cases.bookings.reschedule_booking_use_case import RescheduleBookingUseCase
from app.use_cases.bookings.update_booking_use_case import UpdateBookingUseCase


class BookingUseCasesContainer(containers.DeclarativeContainer):
    """
    Bookings made by the assistant and by staff, and their reminders. The
    booking tools share the business lock registry.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    check_availability_use_case: Factory[
        UseCaseContract[AvailabilityQuery, AvailabilityResult]
    ] = Factory(
        CheckAvailabilityUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    create_booking_use_case: Factory[
        UseCaseContract[CreateBookingCommand, BookingResult]
    ] = Factory(
        CreateBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.booking_confirmation_transformer,
        staff_notification_transformer=transformers.new_booking_notification_transformer,
        staff_brief_transformer=transformers.staff_alert_brief_transformer,
        staff_alerts=facilitators.staff_alert_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    cancel_booking_use_case: Factory[
        UseCaseContract[CancelBookingCommand, BookingResult]
    ] = Factory(
        CancelBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.cancellation_confirmation_transformer,
        staff_notification_transformer=transformers.booking_cancelled_notification_transformer,
        staff_brief_transformer=transformers.staff_alert_brief_transformer,
        staff_alerts=facilitators.staff_alert_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    reschedule_booking_use_case: Factory[
        UseCaseContract[RescheduleBookingCommand, BookingResult]
    ] = Factory(
        RescheduleBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.reschedule_confirmation_transformer,
        staff_notification_transformer=transformers.booking_moved_notification_transformer,
        staff_brief_transformer=transformers.staff_alert_brief_transformer,
        staff_alerts=facilitators.staff_alert_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_bookings_use_case: Factory[UseCaseContract[ListBookingsQuery, BookingPage]] = (
        Factory(
            ListBookingsUseCase,
            business_repo=repositories.business_repo,
            booking_repo=repositories.booking_repo,
            resource_repo=repositories.resource_repo,
            contact_repo=repositories.contact_repo,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    create_manual_booking_use_case: Factory[
        UseCaseContract[ManualBookingCommand, BookingResult]
    ] = Factory(
        CreateManualBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.booking_confirmation_transformer,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_booking_use_case: Factory[
        UseCaseContract[UpdateBookingCommand, BookingView]
    ] = Factory(
        UpdateBookingUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        resource_repo=repositories.resource_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        calendar_sync=facilitators.calendar_sync_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_booking_reminders_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            SendBookingRemindersUseCase,
            business_repo=repositories.business_repo,
            business_profile_repo=repositories.business_profile_repo,
            booking_repo=repositories.booking_repo,
            resource_repo=repositories.resource_repo,
            contact_repo=repositories.contact_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            channel_message_sender=facilitators.channel_message_sender,
            reminder_transformer=transformers.booking_reminder_transformer,
            reminder_template_transformer=(
                transformers.booking_reminder_template_transformer
            ),
            wall_clock=time_provider.microsecond_wall_clock,
            whatsapp_reminder_template=(
                config.app_settings.provided.whatsapp_reminder_template_name
            ),
        )
    )

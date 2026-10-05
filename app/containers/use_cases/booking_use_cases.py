from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
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
from app.schemas.dto.customer_bookings import CustomerBookingList, CustomerBookingsQuery
from app.schemas.dto.jobs import (
    JobReport,
    JobTick,
)
from app.schemas.dto.operations.bookings import (
    BookingPage,
    ListBookingsQuery,
    ManualBookingCommand,
    RevertBookingStatusCommand,
    UpdateBookingCommand,
)
from app.use_cases.bookings.cancel_booking_use_case import CancelBookingUseCase
from app.use_cases.bookings.check_availability_use_case import CheckAvailabilityUseCase
from app.use_cases.bookings.create_booking_use_case import CreateBookingUseCase
from app.use_cases.bookings.list_bookings_use_case import ListBookingsUseCase
from app.use_cases.bookings.list_customer_bookings_use_case import (
    ListCustomerBookingsUseCase,
)
from app.use_cases.bookings.manual_booking.create_manual_booking_use_case import (
    CreateManualBookingUseCase,
)
from app.use_cases.bookings.reminders.send_booking_reminders_use_case import (
    SendBookingRemindersUseCase,
)
from app.use_cases.bookings.reschedule_booking_use_case import RescheduleBookingUseCase
from app.use_cases.bookings.revert_booking_status_use_case import (
    RevertBookingStatusUseCase,
)
from app.use_cases.bookings.update_booking_use_case import UpdateBookingUseCase


class BookingUseCasesContainer(containers.DeclarativeContainer):
    """
    Bookings made by the assistant and by staff, and their reminders. The
    booking tools share the business lock registry.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
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
        knowledge_item_repo=repositories.knowledge_item_repo,
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
        knowledge_item_repo=repositories.knowledge_item_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.booking_confirmation_transformer,
        staff_notification_transformer=transformers.new_booking_notification_transformer,
        staff_brief_transformer=transformers.staff_alert_brief_transformer,
        staff_alerts=facilitators.staff_alert_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        live_events=facilitators.event_publisher,
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
        live_events=facilitators.event_publisher,
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
        knowledge_item_repo=repositories.knowledge_item_repo,
        contact_repo=repositories.contact_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.reschedule_confirmation_transformer,
        staff_notification_transformer=transformers.booking_moved_notification_transformer,
        staff_brief_transformer=transformers.staff_alert_brief_transformer,
        staff_alerts=facilitators.staff_alert_facilitator,
        calendar_sync=facilitators.calendar_sync_facilitator,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The customer's own bookings to come (model tool list_my_bookings).
    list_customer_bookings_use_case: Factory[
        UseCaseContract[CustomerBookingsQuery, CustomerBookingList]
    ] = Factory(
        ListCustomerBookingsUseCase,
        business_repo=repositories.business_repo,
        contact_repo=repositories.contact_repo,
        booking_repo=repositories.booking_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_bookings_use_case: Factory[UseCaseContract[ListBookingsQuery, BookingPage]] = (
        Factory(
            ListBookingsUseCase,
            business_repo=repositories.business_repo,
            booking_repo=repositories.booking_repo,
            resource_repo=repositories.resource_repo,
            knowledge_item_repo=repositories.knowledge_item_repo,
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
        knowledge_item_repo=repositories.knowledge_item_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        phone_number_parser=utilities.phone_number_parser,
        confirmation_transformer=transformers.booking_confirmation_transformer,
        calendar_sync=facilitators.calendar_sync_facilitator,
        live_events=facilitators.event_publisher,
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
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    revert_booking_status_use_case: Factory[
        UseCaseContract[RevertBookingStatusCommand, BookingView]
    ] = Factory(
        RevertBookingStatusUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        booking_repo=repositories.booking_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        lock_registry=registries.business_lock_registry,
        calendar_sync=facilitators.calendar_sync_facilitator,
        live_events=facilitators.event_publisher,
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
            channel_repo=repositories.channel_repo,
            outbound_message_repo=repositories.outbound_message_repo,
            job_queue=facilitators.job_queue_facilitator,
            reminder_transformer=transformers.booking_reminder_transformer,
            reminder_template_transformer=(
                transformers.booking_reminder_template_transformer
            ),
            wall_clock=time_provider.microsecond_wall_clock,
            rate_limits=registries.request_rate_limit_registry,
            suppression_list=facilitators.suppression_list,
            whatsapp_reminder_template=(
                config.app_settings.provided.whatsapp_reminder_template_name
            ),
            unit_of_work=adapters.storage_unit_of_work,
        )
    )

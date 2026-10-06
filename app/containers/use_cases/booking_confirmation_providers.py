"""
The provider of the guest's written confirmation after the assistant books
or moves (`BookingUseCasesContainer.send_booking_confirmation_use_case`),
built from the booking container's edges.
"""

from dependency_injector.providers import Factory, Provider

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
)
from app.use_cases.bookings.confirmations.confirmation_delivery import (
    BookingConfirmationDelivery,
)
from app.use_cases.bookings.confirmations.confirmation_message import (
    ConfirmationWriter,
)
from app.use_cases.bookings.confirmations.send_booking_confirmation_use_case import (
    SendBookingConfirmationUseCase,
)
from app.use_cases.bookings.guest_booking import GuestBookingReader


def booking_confirmation_use_case(
    guest_booking_reader: Provider[GuestBookingReader],
    repositories: RepositoriesContainer,
    facilitators: FacilitatorsContainer,
    adapters: AdaptersContainer,
    time_provider: TimeProviderContainer,
    config: ConfigContainer,
    utilities: UtilitiesContainer,
) -> Factory[UseCaseContract[BookingConfirmationRequest, BookingConfirmationReceipt]]:
    """
    The confirmation use case: the outbox delivery (the guest's channel,
    a WhatsApp template outside the 24-hour window) and the written text
    with the manage link.
    """

    repos: RepositoriesContainer = repositories
    settings = config.app_settings.provided
    return Factory(
        SendBookingConfirmationUseCase,
        guest_bookings=guest_booking_reader,
        conversation_repo=repos.conversation_repo,
        delivery=Factory(
            BookingConfirmationDelivery,
            contact_repo=repos.contact_repo,
            conversation_repo=repos.conversation_repo,
            message_repo=repos.message_repo,
            channel_repo=repos.channel_repo,
            outbound_message_repo=repos.outbound_message_repo,
            job_queue=facilitators.job_queue_facilitator,
            live_events=facilitators.event_publisher,
            unit_of_work=adapters.storage_unit_of_work,
            wall_clock=time_provider.microsecond_wall_clock,
            whatsapp_template=settings.whatsapp_booking_confirmation_template_name,
        ),
        writer=Factory(
            ConfirmationWriter,
            text_resolver=utilities.localized_text_resolver,
        ),
        link_signer=utilities.booking_manage_token_signer,
        cabinet_base_url=settings.cabinet_base_url,
    )

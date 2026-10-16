from typed_time_provider import Microseconds

from app.contracts.booking_links import BookingManageTokenSignerContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
    BookingManageClaims,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageLink
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.use_cases.bookings.confirmations.confirmation_delivery import (
    CONFIRMABLE_CHANNELS,
    BookingConfirmationDelivery,
    ConfirmationLetter,
)
from app.use_cases.bookings.confirmations.confirmation_message import (
    ConfirmationFacts,
    ConfirmationWriter,
)
from app.use_cases.bookings.guest_booking import GuestBooking, GuestBookingReader
from app.utilities.bookings.booking_manage_links import (
    build_manage_link,
    manage_link_expiry,
)


class SendBookingConfirmationUseCase(
    UseCaseContract[BookingConfirmationRequest, BookingConfirmationReceipt]
):
    """
    Confirm a booking to its guest in writing, in the chat it was made in:
    the business, the local date and time, the party, the service, the
    address with a map link and a signed link to the booking's own page
    (/r/{token}: details, a calendar file, cancel, move, write to us). The
    link names the booking's current start time, so after a move only the
    newest confirmation's link manages it.

    The website chat shows it as a message of the conversation; messengers
    get it through the outbox (`BookingConfirmationDelivery`), once per
    booking and start time. The guest asked for the booking, so this is
    a requested message: opt-outs of unrequested messages do not stop it.
    Test chats, bookings made outside a chat (the cabinet, the phone) and
    conversations whose channel cannot carry it get nothing; the receipt
    says whether it went on its way.
    """

    def __init__(
        self,
        guest_bookings: GuestBookingReader,
        conversation_repo: ConversationRepoContract,
        delivery: BookingConfirmationDelivery,
        writer: ConfirmationWriter,
        link_signer: BookingManageTokenSignerContract,
        cabinet_base_url: CabinetBaseUrl | None,
    ) -> None:
        self._guest_bookings: GuestBookingReader = guest_bookings
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._delivery: BookingConfirmationDelivery = delivery
        self._writer: ConfirmationWriter = writer
        self._link_signer: BookingManageTokenSignerContract = link_signer
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url

    def run(self, input_data: BookingConfirmationRequest) -> BookingConfirmationReceipt:
        guest_booking: GuestBooking | None = self._guest_bookings.read(
            input_data.business_id, input_data.booking_id
        )
        if (
            guest_booking is None
            or guest_booking.booking.is_sandbox
            or guest_booking.booking.conversation_id is None
        ):
            return BookingConfirmationReceipt(is_queued=False)

        conversation: ConversationDocument | None = self._conversation_repo.get(
            input_data.business_id, guest_booking.booking.conversation_id
        )
        if (
            conversation is None
            or conversation.is_sandbox
            or conversation.channel not in CONFIRMABLE_CHANNELS
        ):
            return BookingConfirmationReceipt(is_queued=False)

        manage_link: BookingManageLink | None = self._manage_link(guest_booking)
        facts = ConfirmationFacts(
            business=guest_booking.business,
            booking=guest_booking.booking,
            booking_unit=guest_booking.booking_unit,
            service_title=guest_booking.service_title,
            address=(
                None if guest_booking.profile is None else guest_booking.profile.address
            ),
            manage_link=manage_link,
            change=input_data.change,
            language=self._language(input_data, guest_booking),
        )
        is_queued: bool = self._delivery.deliver(
            guest_booking.business,
            conversation,
            guest_booking.booking,
            ConfirmationLetter(
                text=self._writer.text(facts),
                template_parameters=self._writer.template_parameters(facts),
                language=facts.language,
            ),
        )
        return BookingConfirmationReceipt(
            is_queued=is_queued,
            channel=conversation.channel,
            manage_link=manage_link,
        )

    def _manage_link(self, guest_booking: GuestBooking) -> BookingManageLink | None:
        booking = guest_booking.booking
        token = self._link_signer.sign(
            BookingManageClaims(
                business_id=booking.business_id,
                booking_id=booking.id,
                booking_version=booking.starts_at,
                expires_at=Microseconds(int(manage_link_expiry(booking.ends_at))),
            )
        )
        return build_manage_link(self._cabinet_base_url, token)

    @staticmethod
    def _language(
        input_data: BookingConfirmationRequest,
        guest_booking: GuestBooking,
    ) -> LanguageTag:
        return (
            input_data.language
            or guest_booking.booking.language
            or guest_booking.business.default_language
        )

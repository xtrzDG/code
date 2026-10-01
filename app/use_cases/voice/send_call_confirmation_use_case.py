import logging

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories import (
    BookingRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
    ContactRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import CallOutcome
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.booleans import IsCallConfirmationSent
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_texts import (
    CALL_BOOKING_CONFIRMATION_TEXT,
    CALL_BOOKING_PARTY_TEXT,
)
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.local_moments import format_local_moment

logger: logging.Logger = logging.getLogger(__name__)

# Messengers tried for the confirmation, best first: Telegram has no
# messaging window and costs nothing; WhatsApp is where most callers are.
CONFIRMATION_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.WHATSAPP,
    ChannelKind.MESSENGER,
    ChannelKind.INSTAGRAM,
)


class SendCallConfirmationUseCase(
    UseCaseContract[RecordedCall, IsCallConfirmationSent]
):
    """
    After a call that booked, confirm the booking in writing (concept
    section 7: the agent repeats date, time and name aloud, then the
    confirmation goes to a messenger).

    The caller must already be known in a messenger the business has
    connected; the first that delivers is used. The text is in the call's
    language with the date and time in the business's time zone. Delivery
    problems are logged; the call stays recorded either way.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        contact_repo: ContactRepoContract,
        channel_repo: ChannelRepoContract,
        channel_message_sender: ChannelMessageSenderFacilitatorContract,
        text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._channel_message_sender: ChannelMessageSenderFacilitatorContract = (
            channel_message_sender
        )
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def run(self, input_data: RecordedCall) -> IsCallConfirmationSent:
        if (
            input_data.status is not PostCallEventStatus.RECORDED
            or input_data.outcome is not CallOutcome.BOOKING
            or input_data.business_id is None
            or input_data.contact_id is None
            or not input_data.booking_ids
        ):
            return False

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        contact: ContactDocument | None = self._contact_repo.get(
            input_data.business_id,
            input_data.contact_id,
        )
        booking: BookingDocument | None = self._booking_repo.get(
            input_data.business_id,
            input_data.booking_ids[-1],
        )
        if business is None or contact is None or booking is None:
            return False

        language: LanguageTag = input_data.language or business.default_language
        text = MessageText(self._build_text(business, booking, language))
        for identity in self._list_reachable_identities(business, contact):
            try:
                self._channel_message_sender.send(
                    business.id,
                    identity.channel,
                    identity.channel_user_id,
                    text,
                )
            except ExternalServiceError as error:
                logger.warning(
                    "Call confirmation through %s failed: %s",
                    identity.channel.value,
                    error,
                )
                continue

            return True

        return False

    def _build_text(
        self,
        business: BusinessDocument,
        booking: BookingDocument,
        language: LanguageTag,
    ) -> str:
        confirmation: str = str(
            self._text_resolver.resolve(CALL_BOOKING_CONFIRMATION_TEXT, language)
        ).format(
            business=business.name,
            when=format_local_moment(
                int(booking.starts_at), business.timezone, language
            ),
        )
        if booking.party_size <= 1:
            return confirmation

        party: str = str(
            self._text_resolver.resolve(CALL_BOOKING_PARTY_TEXT, language)
        ).format(party_size=int(booking.party_size))
        return f"{confirmation} {party}"

    def _list_reachable_identities(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
    ) -> list[ChannelIdentity]:
        connected_channels: set[ChannelKind] = set()
        for channel_kind in CONFIRMATION_CHANNELS:
            channel: ChannelDocument | None = find_business_channel(
                self._channel_repo,
                business.id,
                channel_kind,
            )
            if channel is not None and channel.status is ChannelStatus.CONNECTED:
                connected_channels.add(channel_kind)

        identities: list[ChannelIdentity] = [
            identity
            for identity in contact.channel_identities
            if identity.channel in connected_channels
        ]
        return sorted(
            identities,
            key=lambda identity: CONFIRMATION_CHANNELS.index(identity.channel),
        )

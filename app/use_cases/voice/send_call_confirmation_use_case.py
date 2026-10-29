from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.conversations import CallOutcome
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.channels.booleans import IsCallConfirmationSent
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.voice.call_message_outbox import CallMessageOutbox
from app.utilities.channels.channel_texts import (
    CALL_BOOKING_CONFIRMATION_TEXT,
    CALL_BOOKING_PARTY_TEXT,
)
from app.utilities.channels.local_moments import format_local_moment


class SendCallConfirmationUseCase(
    UseCaseContract[RecordedCall, IsCallConfirmationSent]
):
    """
    After a call that booked, confirm the booking in writing (concept
    section 7: the agent repeats date, time and name aloud, then the
    confirmation goes to a messenger).

    The caller must already be known in a messenger the business has
    connected that can carry it now (`CallMessageOutbox`); the message goes
    into the outbox once per call and the worker sends it with retries.
    The text is in the call's language with the date and time in the
    business's time zone. True when it was queued.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        contact_repo: ContactRepoContract,
        call_messages: CallMessageOutbox,
        text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._call_messages: CallMessageOutbox = call_messages
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def run(self, input_data: RecordedCall) -> IsCallConfirmationSent:
        if (
            input_data.status is not PostCallEventStatus.RECORDED
            or input_data.outcome is not CallOutcome.BOOKING
            or input_data.business_id is None
            or input_data.call_id is None
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
        return self._call_messages.queue(
            business,
            contact,
            input_data.call_id,
            OutboundMessageKind.CALL_CONFIRMATION,
            text,
        )

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

"""
How a confirmation reaches a messenger: through the outbox, after a short
hold, given up past the booking's start; WhatsApp outside its 24-hour
window takes the approved template (when configured), Messenger and
Instagram there get nothing. The same booking and start are confirmed once.
"""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingConfirmationChange
from app.schemas.constants.channels import ChannelKind, ChannelStatus, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.use_cases.bookings.confirmations.confirmation_delivery import (
    confirmation_key,
)
from app.utilities.deliveries.delivery_keys import derive_outbound_message_id
from tests.bookings.conftest import CABINET_BASE_URL
from tests.bookings.manage_journey import BookedTable, book_a_table
from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

TEMPLATE: str = "booking_confirmation"
GUEST_ADDRESS: str = "995555123456"


@pytest.fixture
def templated() -> Iterator[Workshop]:
    workshop = start_workshop(
        {
            **E2E_ENVIRONMENT,
            "CABINET_BASE_URL": CABINET_BASE_URL,
            "WHATSAPP_BOOKING_CONFIRMATION_TEMPLATE": TEMPLATE,
        }
    )
    with workshop.client:
        yield workshop


@dataclass(frozen=True)
class Confirmed:
    receipt: BookingConfirmationReceipt
    queued: OutboundMessageDocument | None
    booking: BookingDocument


def confirm_in(
    workshop: Workshop,
    booked: BookedTable,
    channel: ChannelKind,
    *,
    guest_wrote: bool,
    status: ChannelStatus = ChannelStatus.CONNECTED,
) -> Confirmed:
    """Move the booking's chat to `channel`, then confirm it there."""

    container = workshop.container
    business_id = BusinessId(booked.restaurant.business_id)
    claims = container.utilities.booking_manage_token_signer().read(
        BookingManageToken(booked.token)
    )
    assert claims is not None
    now: Microseconds = workshop.clock.wall_clock.now_unix()
    with container.utilities.storage_scope().scoped_to_business(business_id):
        bookings = container.repositories.booking_repo()
        conversations = container.repositories.conversation_repo()
        booking = bookings.get(business_id, claims.booking_id)
        assert booking is not None and booking.conversation_id is not None
        widget_chat = conversations.get(business_id, booking.conversation_id)
        assert widget_chat is not None
        container.repositories.channel_repo().save(
            ChannelDocument(
                business_id=business_id,
                kind=channel,
                external_id=ChannelExternalId("100200300"),
                status=status,
            )
        )
        chat = ConversationDocument(
            business_id=business_id,
            contact_id=booking.contact_id,
            assistant_version_id=widget_chat.assistant_version_id,
            channel=channel,
            channel_user_id=ChannelUserId(GUEST_ADDRESS),
            last_message_at=now,
        )
        conversations.save(chat)
        if guest_wrote:
            container.repositories.message_repo().save(
                MessageDocument(
                    conversation_id=chat.id,
                    business_id=business_id,
                    direction=MessageDirection.INBOUND,
                    author=MessageAuthor.CUSTOMER,
                    text=MessageText("Спасибо!"),
                    channel=channel,
                    created_at=now,
                    updated_at=now,
                )
            )
        booking = booking.model_copy(
            update={"conversation_id": chat.id, "source_channel": channel}
        )
        bookings.save(booking)
        receipt = container.use_cases.bookings.send_booking_confirmation_use_case().run(
            BookingConfirmationRequest(
                business_id=business_id,
                booking_id=booking.id,
                change=BookingConfirmationChange.BOOKED,
            )
        )
        queued = container.repositories.outbound_message_repo().get(
            business_id,
            derive_outbound_message_id(business_id, confirmation_key(booking)),
        )
    return Confirmed(receipt=receipt, queued=queued, booking=booking)


def test_whatsapp_within_the_window_gets_the_text(templated: Workshop) -> None:
    booked = book_a_table(templated)

    confirmed = confirm_in(templated, booked, ChannelKind.WHATSAPP, guest_wrote=True)

    assert confirmed.receipt.is_queued is True
    assert confirmed.receipt.channel is ChannelKind.WHATSAPP
    assert str(confirmed.receipt.manage_link).startswith(f"{CABINET_BASE_URL}/r/")
    queued = confirmed.queued
    assert queued is not None
    assert queued.kind is OutboundMessageKind.BOOKING_CONFIRMATION
    assert queued.template is None
    assert str(queued.text).startswith("Salobie Bia: ваша бронь подтверждена.")
    assert queued.booking_id == confirmed.booking.id
    # Held a few seconds behind the assistant's answer; useless after the start.
    assert int(queued.next_attempt_at or 0) - int(queued.created_at) == 5_000_000
    assert int(queued.send_before or 0) == int(confirmed.booking.starts_at) * 1_000_000


def test_whatsapp_outside_the_window_takes_the_template(templated: Workshop) -> None:
    booked = book_a_table(templated)

    confirmed = confirm_in(templated, booked, ChannelKind.WHATSAPP, guest_wrote=False)

    assert confirmed.receipt.is_queued is True
    queued = confirmed.queued
    assert queued is not None and queued.template is not None
    assert str(queued.template.name) == TEMPLATE
    assert str(queued.template.language_code) == "ru"
    business, when, guests, link = [
        str(value) for value in queued.template.body_parameters
    ]
    assert (business, guests) == ("Salobie Bia", "2")
    assert "19:00" in when
    assert link == str(confirmed.receipt.manage_link)


def test_a_confirmation_is_queued_once_per_start(templated: Workshop) -> None:
    booked = book_a_table(templated)
    first = confirm_in(templated, booked, ChannelKind.WHATSAPP, guest_wrote=True)
    assert first.queued is not None

    container = templated.container
    business_id = BusinessId(booked.restaurant.business_id)
    with container.utilities.storage_scope().scoped_to_business(business_id):
        container.use_cases.bookings.send_booking_confirmation_use_case().run(
            BookingConfirmationRequest(
                business_id=business_id,
                booking_id=first.booking.id,
                change=BookingConfirmationChange.BOOKED,
            )
        )
        waiting = container.repositories.outbound_message_repo()
        pending = waiting.list_pending_for_recipient(
            business_id, first.queued.recipient_key
        )

    assert [message.id for message in pending] == [first.queued.id]


def test_without_the_template_whatsapp_outside_the_window_gets_nothing(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)

    confirmed = confirm_in(workshop, booked, ChannelKind.WHATSAPP, guest_wrote=False)

    assert confirmed.receipt.is_queued is False
    assert confirmed.queued is None


@pytest.mark.parametrize("channel", [ChannelKind.MESSENGER, ChannelKind.INSTAGRAM])
def test_meta_chats_outside_the_window_get_nothing(
    templated: Workshop, channel: ChannelKind
) -> None:
    booked = book_a_table(templated)

    confirmed = confirm_in(templated, booked, channel, guest_wrote=False)

    assert confirmed.receipt.is_queued is False
    assert confirmed.queued is None


def test_a_disconnected_channel_gets_nothing(templated: Workshop) -> None:
    booked = book_a_table(templated)

    confirmed = confirm_in(
        templated,
        booked,
        ChannelKind.TELEGRAM,
        guest_wrote=True,
        status=ChannelStatus.DISABLED,
    )

    assert confirmed.receipt.is_queued is False
    assert confirmed.queued is None

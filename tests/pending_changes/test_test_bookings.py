"""
Test bookings take a table only inside their own test conversation: the
bookings earlier checks and test chats left behind no longer fill the
calendar of the next check (PLAN 15.4.5), and real customers never see
any of them.
"""

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.utilities.scheduling.availability import is_blocking

EARLIER_CHECK = ConversationId()
THIS_CHECK = ConversationId()


def booking(
    is_sandbox: bool,
    conversation_id: ConversationId | None = None,
    status: BookingStatus = BookingStatus.CONFIRMED,
) -> BookingDocument:
    return BookingDocument(
        business_id=BusinessId(),
        resource_id=ResourceId(),
        contact_id=ContactId(),
        conversation_id=conversation_id,
        starts_at=BookingStartsAtUnixSeconds(1_790_100_000),
        ends_at=BookingEndsAtUnixSeconds(1_790_107_200),
        party_size=PartySize(2),
        status=status,
        source_channel=ChannelKind.OWNER_TEST,
        is_sandbox=is_sandbox,
    )


def test_real_bookings_block_every_conversation() -> None:
    real = booking(is_sandbox=False)

    assert is_blocking(real, include_sandbox=False)
    assert is_blocking(real, include_sandbox=True, sandbox_conversation_id=THIS_CHECK)


def test_a_test_booking_blocks_only_its_own_test_conversation() -> None:
    left_behind = booking(is_sandbox=True, conversation_id=EARLIER_CHECK)
    own = booking(is_sandbox=True, conversation_id=THIS_CHECK)

    assert not is_blocking(
        left_behind, include_sandbox=True, sandbox_conversation_id=THIS_CHECK
    )
    assert is_blocking(own, include_sandbox=True, sandbox_conversation_id=THIS_CHECK)
    # Real customers never see test bookings.
    assert not is_blocking(own, include_sandbox=False)


def test_without_a_conversation_every_test_booking_still_counts() -> None:
    """The owner's manual checks in the cabinet (no test conversation) see them all."""

    assert is_blocking(
        booking(is_sandbox=True, conversation_id=EARLIER_CHECK), include_sandbox=True
    )


def test_cancelled_bookings_never_block() -> None:
    cancelled = booking(is_sandbox=False, status=BookingStatus.CANCELLED)

    assert not is_blocking(cancelled, include_sandbox=True)

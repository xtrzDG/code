"""
Idempotency keys of the messages a customer gets besides the assistant's
replies: each one is queued in the outbox once, however often the step
that queues it runs (a retried request, a job after a restart, a webhook
the platform repeated).
"""

from app.schemas.constants.bookings import BookingReminderKind
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.conversations.prefixed_id import CallId, MessageId
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey


def staff_reply_idempotency_key(message_id: MessageId) -> OutboundIdempotencyKey:
    """One outbox message per staff message stored in a transcript."""

    return OutboundIdempotencyKey(f"staff_reply:{message_id}")


def reminder_idempotency_key(
    booking_id: BookingId,
    reminder_kind: BookingReminderKind,
    starts_at: BookingStartsAtUnixSeconds,
) -> OutboundIdempotencyKey:
    """
    One reminder of each kind per booking and start time: a moved booking
    is reminded of its new time, never twice of the same one.
    """

    return OutboundIdempotencyKey(
        f"reminder:{booking_id}:{reminder_kind.value}:{int(starts_at)}"
    )


def call_message_idempotency_key(
    call_id: CallId,
    kind: OutboundMessageKind,
) -> OutboundIdempotencyKey:
    """One message of each kind (confirmation, links) after a call."""

    return OutboundIdempotencyKey(f"{kind.value}:{call_id}")


def text_back_idempotency_key(missed_call_id: MissedCallId) -> OutboundIdempotencyKey:
    """One WhatsApp text-back per missed call."""

    return OutboundIdempotencyKey(f"text_back:{missed_call_id}")

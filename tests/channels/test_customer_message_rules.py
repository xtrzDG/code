"""
Rules of the messages a customer gets besides the assistant's replies:
their idempotency keys, why a failed send failed in the cabinet's terms,
the delivery state a staff reply shows, and a message whose moment passed.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingReminderKind
from app.schemas.constants.calls import MissedCallSource
from app.schemas.constants.deliveries import (
    DeliveryFailureReason,
    OutboundDeliveryState,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ConflictError,
    DeliveryNotConfiguredError,
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import CallId, MessageId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.deliveries.constrained_integers import DeliveryAttemptCount
from app.utilities.calls.call_follow_up_keys import missed_call_id_of
from app.utilities.deliveries.customer_message_keys import (
    call_message_idempotency_key,
    reminder_idempotency_key,
    staff_reply_idempotency_key,
    text_back_idempotency_key,
)
from app.utilities.deliveries.delivery_views import delivery_state_of
from app.utilities.deliveries.retry_policy import explain_delivery_error
from tests.channels.customer_outbox import queue_customer_message
from tests.channels.telegram_updates import connect_bot
from tests.channels.testbed import ChannelsTestbed


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (ProviderRateLimitedError("429"), DeliveryFailureReason.RATE_LIMITED),
        (
            ChannelCredentialRejectedError("401"),
            DeliveryFailureReason.CREDENTIAL_REJECTED,
        ),
        (DeliveryNotConfiguredError("none"), DeliveryFailureReason.NOT_CONFIGURED),
        (
            WhatsAppTemplateRejectedError("132001"),
            DeliveryFailureReason.TEMPLATE_REJECTED,
        ),
        (
            ProviderRejectedMessageError("blocked"),
            DeliveryFailureReason.RECIPIENT_REFUSED,
        ),
        (ExternalServiceError("500"), DeliveryFailureReason.PROVIDER_UNAVAILABLE),
        (ConflictError("gone"), DeliveryFailureReason.CHANNEL_DISCONNECTED),
    ],
)
def test_a_send_error_is_explained_to_the_owner(
    error: ApplicationError, reason: DeliveryFailureReason
) -> None:
    assert explain_delivery_error(error) is reason


def test_each_customer_message_has_one_key_per_occasion() -> None:
    booking_id, call_id = BookingId(), CallId()
    message_id = MessageId()
    missed_call_id = missed_call_id_of(
        BusinessId(), MissedCallSource.PBX, ProviderCallId("call-1")
    )
    starts_at = BookingStartsAtUnixSeconds(1_791_041_400)
    moved = BookingStartsAtUnixSeconds(1_791_045_000)
    day_before = BookingReminderKind.DAY_BEFORE

    assert reminder_idempotency_key(booking_id, day_before, starts_at) == (
        reminder_idempotency_key(booking_id, day_before, starts_at)
    )
    assert reminder_idempotency_key(booking_id, day_before, starts_at) != (
        reminder_idempotency_key(booking_id, day_before, moved)
    )
    assert call_message_idempotency_key(
        call_id, OutboundMessageKind.CALL_CONFIRMATION
    ) != call_message_idempotency_key(call_id, OutboundMessageKind.CALL_LINKS)
    keys = {
        str(staff_reply_idempotency_key(message_id)),
        str(text_back_idempotency_key(missed_call_id)),
        str(reminder_idempotency_key(booking_id, day_before, starts_at)),
        str(call_message_idempotency_key(call_id, OutboundMessageKind.CALL_LINKS)),
    }
    assert len(keys) == 4


def waiting_message(testbed: ChannelsTestbed) -> OutboundMessageDocument:
    _, channel = connect_bot(testbed)
    return queue_customer_message(
        testbed, channel, "555000111", OutboundMessageKind.CALL_LINKS
    )


@pytest.mark.parametrize(
    ("status", "attempts", "state"),
    [
        (OutboundMessageStatus.PENDING, 0, OutboundDeliveryState.SENDING),
        (OutboundMessageStatus.PENDING, 2, OutboundDeliveryState.RETRYING),
        (OutboundMessageStatus.DELIVERED, 1, OutboundDeliveryState.DELIVERED),
        (OutboundMessageStatus.DEAD, 8, OutboundDeliveryState.FAILED),
    ],
)
def test_the_delivery_state_a_reply_shows(
    status: OutboundMessageStatus, attempts: int, state: OutboundDeliveryState
) -> None:
    message = waiting_message(ChannelsTestbed()).model_copy(
        update={"status": status, "attempts": DeliveryAttemptCount(attempts)}
    )

    assert delivery_state_of(message) is state


def test_a_message_whose_moment_passed_is_given_up_unsent() -> None:
    testbed = ChannelsTestbed()
    queued = waiting_message(testbed)

    def expire(current: OutboundMessageDocument) -> OutboundMessageDocument:
        current.send_before = Microseconds(int(testbed.wall_clock.now_unix()) - 1)
        return current

    testbed.outbound_message_repo.update(queued.business_id, queued.id, expire)
    testbed.run_worker()

    expired = testbed.outbound_message_repo.get(queued.business_id, queued.id)
    assert expired is not None
    assert expired.status is OutboundMessageStatus.DEAD
    assert expired.last_failure_reason is DeliveryFailureReason.EXPIRED
    assert testbed.telegram_transport.requests_to("/sendMessage") == []

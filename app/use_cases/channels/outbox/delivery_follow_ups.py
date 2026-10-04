"""
What a delivery outcome changes outside the outbox: the health of the
business's channel, the state of the handoff a notification is about and
of the feedback request a message carries.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.deliveries import DeliveryFailureKind, OutboundMessageStatus
from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.deliveries import OutboundAttempt
from app.utilities.channels.channel_activity import stamp_channel_activity
from app.utilities.channels.channel_health import (
    mark_channel_failing,
    mark_channel_working,
    note_channel_refusal,
    reload_same_connection,
)

# Handoff states a delivered notification may move to NOTIFIED (a resolved
# handoff stays resolved).
NOTIFIABLE_HANDOFF_STATUSES: frozenset[HandoffStatus] = frozenset(
    {HandoffStatus.PENDING, HandoffStatus.NOTIFICATION_FAILED}
)


def update_channel_health(
    channel_repo: ChannelRepoContract,
    live_events: EventPublisherFacilitatorContract,
    message: OutboundMessageDocument,
    attempt: OutboundAttempt,
    now: Microseconds,
) -> None:
    """
    A delivered reply shows the channel works (and clears an old error) and
    is the channel's latest outgoing message (`last_outbound_at`, to the
    minute); a refused credential puts it in ERROR; a reply refused for
    good (a 4xx, or every retry failed) leaves its reason for the owner to
    see, with what it means (`last_failure_reason`). Only while the channel
    still has the connection the reply was sent with: an outcome of a
    replaced token says nothing about the new one.
    """

    if attempt.channel is None:
        return

    channel: ChannelDocument | None = reload_same_connection(
        channel_repo, attempt.channel
    )
    if channel is None:
        return

    if message.status is OutboundMessageStatus.DELIVERED:
        mark_channel_working(channel_repo, live_events, channel, now)
        stamp_channel_activity(channel_repo, channel, MessageDirection.OUTBOUND, now)
        return

    if message.status is not OutboundMessageStatus.DEAD or message.last_error is None:
        return

    if attempt.failure is DeliveryFailureKind.CREDENTIAL_REJECTED:
        mark_channel_failing(
            channel_repo,
            live_events,
            channel,
            str(message.last_error),
            now,
            message.last_failure_reason,
        )
        return

    note_channel_refusal(
        channel_repo,
        live_events,
        channel,
        str(message.last_error),
        now,
        message.last_failure_reason,
    )


def update_handoff_notification(
    handoff_repo: HandoffRepoContract,
    message: OutboundMessageDocument,
    now: Microseconds,
) -> None:
    """
    A delivered notification about a handoff makes it NOTIFIED; a failed
    one makes a handoff that nobody was told about yet NOTIFICATION_FAILED
    (a later delivery to another contact still makes it NOTIFIED).
    """

    if message.handoff_id is None:
        return

    if message.status is OutboundMessageStatus.DELIVERED:
        move_handoff(handoff_repo, message, now, notified_handoff)
    elif message.status is OutboundMessageStatus.DEAD:
        move_handoff(handoff_repo, message, now, failed_handoff)


def move_handoff(
    handoff_repo: HandoffRepoContract,
    message: OutboundMessageDocument,
    now: Microseconds,
    move: Callable[[HandoffDocument], HandoffStatus | None],
) -> None:
    if message.handoff_id is None:
        return

    def change(handoff: HandoffDocument) -> HandoffDocument | None:
        status: HandoffStatus | None = move(handoff)
        if status is None or status is handoff.status:
            return None

        handoff.status = status
        handoff.updated_at = now
        return handoff

    handoff_repo.update(message.business_id, message.handoff_id, change)


def notified_handoff(handoff: HandoffDocument) -> HandoffStatus | None:
    if handoff.status in NOTIFIABLE_HANDOFF_STATUSES:
        return HandoffStatus.NOTIFIED

    return None


def failed_handoff(handoff: HandoffDocument) -> HandoffStatus | None:
    if handoff.status is HandoffStatus.PENDING:
        return HandoffStatus.NOTIFICATION_FAILED

    return None


def update_feedback_request(
    feedback_request_repo: FeedbackRequestRepoContract,
    message: OutboundMessageDocument,
    now: Microseconds,
) -> None:
    """
    A delivered request for feedback notes when it arrived; one given up
    becomes FAILED with the platform's reason (only while it still waits
    for the rating: an answer is never undone).
    """

    if message.feedback_request_id is None or message.status not in (
        OutboundMessageStatus.DELIVERED,
        OutboundMessageStatus.DEAD,
    ):
        return

    def change(request: FeedbackRequestDocument) -> FeedbackRequestDocument | None:
        if request.status is not FeedbackRequestStatus.SENT:
            return None

        if message.status is OutboundMessageStatus.DELIVERED:
            request.delivered_at = now
        else:
            request.status = FeedbackRequestStatus.FAILED
            request.last_error = message.last_error

        request.updated_at = now
        return request

    feedback_request_repo.update(
        message.business_id, message.feedback_request_id, change
    )

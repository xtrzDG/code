"""
Whether a business's channel works: a platform that refuses the channel's
credential puts it in ERROR with a short reason; the next successful
delivery puts it back to CONNECTED.

A channel in ERROR still receives and answers messages (the refusal may be
temporary, and a working delivery is what clears it); the cabinet shows the
reason so the owner can reconnect: the platform's words (`last_error`)
and what they mean in the cabinet's terms (`last_error_reason`, the
outbox's failure reason). A change is written to the channel as stored,
in one step with the check that it still has the account and credential
the outcome was about (`ChannelRepoContract.modify`), so a token renewed
or a channel reconnected meanwhile is never undone, and only the health
fields change. Every change is announced on the cabinet's live stream
(`channel.error` when a channel fails, `channel.changed` otherwise).
"""

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.deliveries import DeliveryFailureReason
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.channels.constrained_strings import ChannelErrorSummary

ACTIVE_CHANNEL_STATUSES: frozenset[ChannelStatus] = frozenset(
    {ChannelStatus.CONNECTED, ChannelStatus.ERROR}
)
# ChannelErrorSummary holds at most this many characters.
MAX_CHANNEL_ERROR_LENGTH: int = 300
UNKNOWN_CHANNEL_ERROR: str = "The platform refused the channel's credential."


def is_channel_active(channel: ChannelDocument) -> bool:
    """Connected, or connected but failing (it still gets every attempt)."""

    return channel.status in ACTIVE_CHANNEL_STATUSES


def summarize_channel_error(reason: str) -> ChannelErrorSummary:
    """A platform's error message on one line, cut to the stored length."""

    text: str = " ".join(reason.split())
    if len(text) > MAX_CHANNEL_ERROR_LENGTH:
        text = text[: MAX_CHANNEL_ERROR_LENGTH - 1].rstrip() + "…"

    return ChannelErrorSummary(text or UNKNOWN_CHANNEL_ERROR)


def reload_same_connection(
    channel_repo: ChannelRepoContract,
    sent_with: ChannelDocument,
) -> ChannelDocument | None:
    """
    The stored channel when it still has the account and credential a
    message was sent with; None when it was reconnected or disabled while
    the message was in flight (that outcome says nothing about the channel
    as it is now, and saving the old copy would undo the change).
    """

    current: ChannelDocument | None = channel_repo.get(sent_with.id)
    if current is None or not has_same_connection(current, sent_with):
        return None

    return current


def has_same_connection(current: ChannelDocument, read: ChannelDocument) -> bool:
    """The channel still has the account and the credential (as sealed) of `read`."""

    return (
        current.encrypted_secret == read.encrypted_secret
        and current.external_id == read.external_id
    )


def mark_channel_failing(
    channel_repo: ChannelRepoContract,
    live_events: EventPublisherFacilitatorContract,
    channel: ChannelDocument,
    reason: str,
    now: Microseconds,
    failure: DeliveryFailureReason | None = None,
) -> None:
    """
    Put an active channel in ERROR with the platform's reason. Like every
    writer here it changes the channel as stored now, and only while it
    still has the connection of `channel` (a token renewed or replaced
    meanwhile is never undone); the live event follows a write only.
    """

    def fail(stored: ChannelDocument) -> ChannelDocument | None:
        if not is_channel_active(stored) or not has_same_connection(stored, channel):
            return None

        stored.status = ChannelStatus.ERROR
        stored.last_error = summarize_channel_error(reason)
        stored.last_error_at = now
        stored.last_error_reason = failure
        stored.updated_at = now
        return stored

    if channel_repo.modify(channel.business_id, channel.id, fail) is not None:
        live_events.publish(
            channel.business_id, LiveEventKind.CHANNEL_ERROR, (channel.id,)
        )


def note_channel_refusal(
    channel_repo: ChannelRepoContract,
    live_events: EventPublisherFacilitatorContract,
    channel: ChannelDocument,
    reason: str,
    now: Microseconds,
    failure: DeliveryFailureReason | None = None,
) -> None:
    """
    The platform refused one message for good (a blocked bot, a closed
    24-hour window): the owner sees the reason, the channel keeps working.
    """

    def note(stored: ChannelDocument) -> ChannelDocument | None:
        if not is_channel_active(stored) or not has_same_connection(stored, channel):
            return None

        stored.last_error = summarize_channel_error(reason)
        stored.last_error_at = now
        stored.last_error_reason = failure
        stored.updated_at = now
        return stored

    if channel_repo.modify(channel.business_id, channel.id, note) is not None:
        live_events.publish(
            channel.business_id, LiveEventKind.CHANNEL_CHANGED, (channel.id,)
        )


def mark_channel_working(
    channel_repo: ChannelRepoContract,
    live_events: EventPublisherFacilitatorContract,
    channel: ChannelDocument,
    now: Microseconds,
) -> None:
    """
    A delivery went through: a channel in ERROR is CONNECTED again and an
    older refusal is no longer shown.
    """

    def heal(stored: ChannelDocument) -> ChannelDocument | None:
        if not has_same_connection(stored, channel):
            return None

        if stored.status is ChannelStatus.ERROR:
            stored.status = ChannelStatus.CONNECTED
        elif stored.status is not ChannelStatus.CONNECTED or stored.last_error is None:
            return None

        stored.last_error = None
        stored.last_error_at = None
        stored.last_error_reason = None
        stored.updated_at = now
        return stored

    if channel_repo.modify(channel.business_id, channel.id, heal) is not None:
        live_events.publish(
            channel.business_id, LiveEventKind.CHANNEL_CHANGED, (channel.id,)
        )

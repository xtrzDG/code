"""
Whether a business's channel works: a platform that refuses the channel's
credential puts it in ERROR with a short reason; the next successful
delivery puts it back to CONNECTED.

A channel in ERROR still receives and answers messages (the refusal may be
temporary, and a working delivery is what clears it); the cabinet shows the
reason so the owner can reconnect.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelStatus
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
    if (
        current is None
        or current.encrypted_secret != sent_with.encrypted_secret
        or current.external_id != sent_with.external_id
    ):
        return None

    return current


def mark_channel_failing(
    channel_repo: ChannelRepoContract,
    channel: ChannelDocument,
    reason: str,
    now: Microseconds,
) -> None:
    """Put an active channel in ERROR with the platform's reason."""

    if not is_channel_active(channel):
        return

    channel.status = ChannelStatus.ERROR
    channel.last_error = summarize_channel_error(reason)
    channel.last_error_at = now
    channel.updated_at = now
    channel_repo.save(channel)


def note_channel_refusal(
    channel_repo: ChannelRepoContract,
    channel: ChannelDocument,
    reason: str,
    now: Microseconds,
) -> None:
    """
    The platform refused one message for good (a blocked bot, a closed
    24-hour window): the owner sees the reason, the channel keeps working.
    """

    if not is_channel_active(channel):
        return

    channel.last_error = summarize_channel_error(reason)
    channel.last_error_at = now
    channel.updated_at = now
    channel_repo.save(channel)


def mark_channel_working(
    channel_repo: ChannelRepoContract,
    channel: ChannelDocument,
    now: Microseconds,
) -> None:
    """
    A delivery went through: a channel in ERROR is CONNECTED again and an
    older refusal is no longer shown.
    """

    if channel.status is not ChannelStatus.ERROR:
        if channel.status is ChannelStatus.CONNECTED and channel.last_error is not None:
            channel.last_error = None
            channel.last_error_at = None
            channel.updated_at = now
            channel_repo.save(channel)

        return

    channel.status = ChannelStatus.CONNECTED
    channel.last_error = None
    channel.last_error_at = None
    channel.updated_at = now
    channel_repo.save(channel)

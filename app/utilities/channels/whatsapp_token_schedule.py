"""
When the platform renews a business's own WhatsApp token (Embedded
Signup's, 60 days) and what the owners hear about it: the tokens a run of
`refresh_whatsapp_tokens` looks at (those that end within the refresh
window, META_TOKEN_REFRESH_DAYS, and those that ended: on a connected
channel however long ago, on one already in ERROR within the last week),
which reminder an outcome calls for, and the subject that lets each
reminder reach each recipient once per token.
"""

from datetime import UTC, datetime

from typed_time_provider import Microseconds

from app.schemas.constants.meta_connection import (
    WhatsAppTokenNoticeStage,
    WhatsAppTokenRefreshOutcome,
)
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.meta_connection.booleans import HasMetaTokenEnded
from app.schemas.typings.meta_connection.constrained_integers import (
    MetaTokenRefreshDays,
)
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_HOUR: int = 60 * 60 * MICROSECONDS_PER_SECOND
MICROSECONDS_PER_DAY: int = 24 * MICROSECONDS_PER_HOUR
# A token that ended on a channel already in ERROR is looked at for this
# long (its ENDED reminder, sent once, is not asked for again after that).
# On a connected channel an ended token is handled however long ago it
# ended: a channel switched back on (a business closure cancelled weeks
# later) still goes to ERROR and its owners still hear.
ENDED_LOOKBACK_MICROSECONDS: int = 7 * MICROSECONDS_PER_DAY
# This close to its end, a token that was not renewed gets the ENDING
# reminder.
ENDING_NOTICE_MICROSECONDS: int = 3 * MICROSECONDS_PER_DAY
# A renewed token must end at least this much later than the one it
# replaces, or Meta did not really extend it. An hour, not a day: a token
# renewed in one run may be renewed again in the next (6 hours later) when
# the refresh window is the token's whole 60 days.
MINIMUM_EXTENSION_MICROSECONDS: int = MICROSECONDS_PER_HOUR
# The channels one run reads, soonest end first, and how many of them it
# asks Meta to renew (the rest wait for the next run).
CHANNELS_READ: DocumentQueryLimit = DocumentQueryLimit(500)
REFRESHES_PER_RUN: int = 100
NOTICE_PREFIX: str = "whatsapp_token"


def refresh_window(
    now: Microseconds, refresh_days: MetaTokenRefreshDays
) -> tuple[Microseconds, Microseconds]:
    """
    The token ends a run looks at: the earliest end of a token whose
    channel is already in ERROR (a week ago, inclusive), and the end before
    which tokens are renewed (`refresh_days` from now, exclusive).
    """

    return (
        Microseconds(int(now) - ENDED_LOOKBACK_MICROSECONDS),
        Microseconds(int(now) + int(refresh_days) * MICROSECONDS_PER_DAY),
    )


def has_token_ended(channel: ChannelDocument, now: Microseconds) -> HasMetaTokenEnded:
    """The channel's token has ended (no Meta call can renew it any more)."""

    ends_at: Microseconds | None = channel.credential_expires_at
    return ends_at is not None and int(ends_at) <= int(now)


def notice_stage(
    ends_at: Microseconds,
    now: Microseconds,
    outcome: WhatsAppTokenRefreshOutcome,
) -> WhatsAppTokenNoticeStage | None:
    """
    The reminder a renewal's outcome calls for: none once a token was
    renewed or replaced; ENDING when three days or less remain; else
    REFRESH_REFUSED when Meta refused, and nothing when it could not be
    asked (the next run tries again).
    """

    if outcome in (
        WhatsAppTokenRefreshOutcome.REFRESHED,
        WhatsAppTokenRefreshOutcome.REPLACED,
    ):
        return None

    if int(ends_at) - int(now) <= ENDING_NOTICE_MICROSECONDS:
        return WhatsAppTokenNoticeStage.ENDING

    if outcome is WhatsAppTokenRefreshOutcome.REFUSED:
        return WhatsAppTokenNoticeStage.REFRESH_REFUSED

    return None


def notice_subject(
    channel_id: ChannelId,
    ends_at: Microseconds,
    stage: WhatsAppTokenNoticeStage,
) -> StaffAlertSubject:
    """
    What makes a reminder the same (its outbox key): the channel, the day
    its token ends (UTC) and the stage. A new token ends another day, so
    its reminders are new.
    """

    day: str = end_moment(ends_at).strftime("%Y%m%d")
    return StaffAlertSubject(f"{NOTICE_PREFIX}:{channel_id}-{day}-{stage.value}")


def notice_tag(channel_id: ChannelId) -> PushNotificationTag:
    """A newer reminder about the channel's token replaces the older on a device."""

    return PushNotificationTag(f"{NOTICE_PREFIX}:{channel_id}")


def end_moment(ends_at: Microseconds) -> datetime:
    """A token's end as a moment in UTC."""

    return datetime.fromtimestamp(int(ends_at) // MICROSECONDS_PER_SECOND, UTC)


def describe_end(ends_at: Microseconds | None) -> str:
    """A token's end for a log line: the UTC moment, or that it has none."""

    return "never" if ends_at is None else end_moment(ends_at).isoformat()

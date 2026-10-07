"""
When an activation nudge is due, as pure rules: the days after the
business was created (no go-live yet) or after it went live (no second
channel or first conversation; no printed QR code or hosted page visit),
a short grace for a run that missed the day, and daytime in the
business's own time zone.
"""

from dataclasses import dataclass
from datetime import datetime

from typed_time_provider import Microseconds

from app.schemas.constants.nudges import NudgeAnchor, NudgeCode, NudgeTopic
from app.schemas.typings.setup.constrained_integers import NudgeDayOffset

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
# A nudge that could not go out on its day still goes out the day after; a
# later one of the same kind replaces it after that.
GRACE_DAYS: int = 2
# Nudges arrive in the business's daytime (local hours, end excluded).
SEND_FROM_HOUR: int = 10
SEND_UNTIL_HOUR: int = 19
ENOUGH_CUSTOMER_CHANNELS: int = 2


@dataclass(frozen=True)
class NudgeRule:
    """A nudge, what its days count from, and the day it is due."""

    code: NudgeCode
    anchor: NudgeAnchor
    day: NudgeDayOffset


NUDGE_RULES: tuple[NudgeRule, ...] = (
    NudgeRule(NudgeCode.NOT_LIVE_DAY_1, NudgeAnchor.CREATION, NudgeDayOffset(1)),
    NudgeRule(NudgeCode.NOT_LIVE_DAY_3, NudgeAnchor.CREATION, NudgeDayOffset(3)),
    NudgeRule(NudgeCode.NOT_LIVE_DAY_7, NudgeAnchor.CREATION, NudgeDayOffset(7)),
    NudgeRule(NudgeCode.LIVE_DAY_2, NudgeAnchor.GO_LIVE, NudgeDayOffset(2)),
    NudgeRule(NudgeCode.LIVE_DAY_5, NudgeAnchor.GO_LIVE, NudgeDayOffset(5)),
    NudgeRule(NudgeCode.LIVE_DAY_10, NudgeAnchor.GO_LIVE, NudgeDayOffset(10)),
)


@dataclass(frozen=True)
class NudgeSituation:
    """
    Where a business stands: when it was created and went live (None: not
    yet), whether it answers customers now (live, not paused), how many
    channels customers can write in, whether a real customer wrote, and
    whether the QR code was printed or saved or the hosted page opened.
    """

    created_at: Microseconds
    went_live_at: Microseconds | None
    is_answering: bool
    customer_channel_count: int
    has_first_conversation: bool
    has_shared: bool


def due_nudge(
    situation: NudgeSituation,
    now: Microseconds,
    local_now: datetime,
) -> NudgeRule | None:
    """
    The nudge due now, if any: the latest rule of the business's stage
    whose day has come (within the grace) and whose condition still holds.
    Whether it was already sent is the caller's to check.
    """

    if not SEND_FROM_HOUR <= local_now.hour < SEND_UNTIL_HOUR:
        return None

    if situation.went_live_at is None:
        anchor, since = NudgeAnchor.CREATION, situation.created_at
    elif situation.is_answering:
        anchor, since = NudgeAnchor.GO_LIVE, situation.went_live_at
    else:
        return None

    elapsed_days: int = (int(now) - int(since)) // MICROSECONDS_PER_DAY
    latest: NudgeRule | None = None
    for rule in NUDGE_RULES:
        if rule.anchor is anchor and int(rule.day) <= elapsed_days:
            latest = rule

    if latest is None or elapsed_days >= int(latest.day) + GRACE_DAYS:
        return None

    return latest if is_still_needed(latest.code, situation) else None


def is_still_needed(code: NudgeCode, situation: NudgeSituation) -> bool:
    """Whether what the nudge asks for is still missing."""

    if code in (NudgeCode.LIVE_DAY_2, NudgeCode.LIVE_DAY_5):
        return (
            situation.customer_channel_count < ENOUGH_CUSTOMER_CHANNELS
            or not situation.has_first_conversation
        )

    if code is NudgeCode.LIVE_DAY_10:
        return not situation.has_shared

    return situation.went_live_at is None


def nudge_topic(code: NudgeCode, situation: NudgeSituation) -> NudgeTopic:
    """
    What the nudge asks for. Day 2 after going live: the link while no
    customer wrote, else a second channel; day 5 the other way round.
    """

    single_channel: bool = situation.customer_channel_count < ENOUGH_CUSTOMER_CHANNELS
    match code:
        case NudgeCode.NOT_LIVE_DAY_1 | NudgeCode.NOT_LIVE_DAY_3:
            return NudgeTopic.FINISH_SETUP
        case NudgeCode.NOT_LIVE_DAY_7:
            return NudgeTopic.DONE_FOR_YOU
        case NudgeCode.LIVE_DAY_2:
            return (
                NudgeTopic.SHARE_LINK
                if not situation.has_first_conversation
                else NudgeTopic.CONNECT_CHANNEL
            )
        case NudgeCode.LIVE_DAY_5:
            return (
                NudgeTopic.CONNECT_CHANNEL if single_channel else NudgeTopic.SHARE_LINK
            )
        case NudgeCode.LIVE_DAY_10:
            return NudgeTopic.PRINT_QR

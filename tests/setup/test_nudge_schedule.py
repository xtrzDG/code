"""When an activation nudge is due and what it asks for, as pure rules."""

from datetime import datetime

from typed_time_provider import Microseconds

from app.schemas.constants.nudges import NudgeCode, NudgeTopic
from app.utilities.setup.nudge_schedule import (
    MICROSECONDS_PER_DAY,
    NudgeSituation,
    due_nudge,
    is_still_needed,
    nudge_topic,
)

CREATED = Microseconds(1_790_000_000_000_000)
NOON = datetime.fromisoformat("2026-10-01T12:00:00+04:00")


def days_later(days: float) -> Microseconds:
    return Microseconds(int(CREATED) + int(days * MICROSECONDS_PER_DAY))


def situation(
    went_live_at: Microseconds | None = None,
    channels: int = 1,
    has_conversation: bool = False,
    has_shared: bool = False,
    is_answering: bool = True,
) -> NudgeSituation:
    return NudgeSituation(
        created_at=CREATED,
        went_live_at=went_live_at,
        is_answering=is_answering,
        customer_channel_count=channels,
        has_first_conversation=has_conversation,
        has_shared=has_shared,
    )


def due(stage: NudgeSituation, days: float, local: datetime = NOON) -> NudgeCode | None:
    rule = due_nudge(stage, days_later(days), local)
    return None if rule is None else rule.code


def test_owners_who_have_not_gone_live_hear_on_days_1_3_and_7() -> None:
    not_live = situation()

    assert due(not_live, 0.5) is None
    assert due(not_live, 1) is NudgeCode.NOT_LIVE_DAY_1
    assert due(not_live, 2.9) is NudgeCode.NOT_LIVE_DAY_1
    assert due(not_live, 3) is NudgeCode.NOT_LIVE_DAY_3
    assert due(not_live, 5) is None
    assert due(not_live, 7.5) is NudgeCode.NOT_LIVE_DAY_7
    # Two days late is too late: nothing older than the grace goes out.
    assert due(not_live, 9) is None
    assert due(not_live, 30) is None


def test_after_going_live_days_2_and_5_wait_for_a_channel_or_a_customer() -> None:
    live = days_later(1)
    alone = situation(went_live_at=live)

    assert due(alone, 2) is None  # one day after going live
    assert due(alone, 3) is NudgeCode.LIVE_DAY_2
    assert due(alone, 6) is NudgeCode.LIVE_DAY_5
    # A second channel and a first customer: nothing to ask for.
    thriving = situation(went_live_at=live, channels=2, has_conversation=True)
    assert due(thriving, 3) is None
    assert due(thriving, 6) is None
    # Either missing is enough.
    assert due(situation(went_live_at=live, channels=3), 3) is NudgeCode.LIVE_DAY_2
    assert (
        due(situation(went_live_at=live, has_conversation=True), 6)
        is NudgeCode.LIVE_DAY_5
    )


def test_day_10_asks_for_the_qr_code_until_it_is_printed_or_the_page_opened() -> None:
    live = days_later(1)

    assert due(situation(went_live_at=live), 11) is NudgeCode.LIVE_DAY_10
    assert due(situation(went_live_at=live, has_shared=True), 11) is None


def test_nudges_wait_for_daytime_and_skip_paused_businesses() -> None:
    not_live = situation()
    night = datetime.fromisoformat("2026-10-01T23:30:00+04:00")
    early = datetime.fromisoformat("2026-10-01T09:59:00+04:00")
    evening = datetime.fromisoformat("2026-10-01T19:00:00+04:00")

    assert due(not_live, 1, night) is None
    assert due(not_live, 1, early) is None
    assert due(not_live, 1, evening) is None
    paused = situation(went_live_at=days_later(1), is_answering=False)
    assert due(paused, 3) is None


def test_going_live_ends_the_reminders_to_finish_the_setup() -> None:
    assert is_still_needed(NudgeCode.NOT_LIVE_DAY_3, situation()) is True
    assert (
        is_still_needed(NudgeCode.NOT_LIVE_DAY_3, situation(went_live_at=CREATED))
        is False
    )


def test_each_nudge_asks_for_the_most_useful_next_thing() -> None:
    live = days_later(1)
    alone = situation(went_live_at=live)
    talking = situation(went_live_at=live, has_conversation=True)
    connected = situation(went_live_at=live, channels=2)

    assert nudge_topic(NudgeCode.NOT_LIVE_DAY_1, alone) is NudgeTopic.FINISH_SETUP
    assert nudge_topic(NudgeCode.NOT_LIVE_DAY_3, alone) is NudgeTopic.FINISH_SETUP
    assert nudge_topic(NudgeCode.NOT_LIVE_DAY_7, alone) is NudgeTopic.DONE_FOR_YOU
    assert nudge_topic(NudgeCode.LIVE_DAY_2, alone) is NudgeTopic.SHARE_LINK
    assert nudge_topic(NudgeCode.LIVE_DAY_2, talking) is NudgeTopic.CONNECT_CHANNEL
    assert nudge_topic(NudgeCode.LIVE_DAY_5, alone) is NudgeTopic.CONNECT_CHANNEL
    assert nudge_topic(NudgeCode.LIVE_DAY_5, connected) is NudgeTopic.SHARE_LINK
    assert nudge_topic(NudgeCode.LIVE_DAY_10, alone) is NudgeTopic.PRINT_QR

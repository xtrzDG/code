"""
The `record_sli` job: customer messages judged per five-minute slot once
their 60 s are over, one row per hour with the answer p95 and the API's
5xx share, a rerun that changes nothing, and old slots and rows removed.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.service_levels import ServiceLevelHourDocument
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from tests.service_levels.sli_world import (
    DAY,
    HOUR,
    HOUR_START,
    MINUTE,
    SECOND,
    SliWorld,
    inbound,
    reply,
)

AFTER_THE_HOUR: int = HOUR + 11 * MINUTE


def only_hour(world: SliWorld) -> ServiceLevelHourDocument:
    [hour] = world.hours.list_all()
    return hour


def test_an_hour_counts_messages_answered_or_handed_off_within_60_s() -> None:
    world = SliWorld()
    world.receive(
        inbound(HOUR_START + 1 * MINUTE, 4 * SECOND),
        inbound(HOUR_START + 7 * MINUTE, 60 * SECOND),
        inbound(
            HOUR_START + 12 * MINUTE,
            20 * SECOND,
            status=InboundEventStatus.HANDED_OFF,
        ),
        inbound(HOUR_START + 20 * MINUTE, 61 * SECOND),  # too late
        inbound(HOUR_START + 30 * MINUTE, None),  # never answered
        inbound(
            HOUR_START + 40 * MINUTE,
            2 * SECOND,
            status=InboundEventStatus.FAILED,
        ),
        # Not customer messages: a platform bot update, one without business.
        inbound(
            HOUR_START + 41 * MINUTE,
            1 * SECOND,
            kind=InboundEventKind.PLATFORM_BOT_UPDATE,
        ),
        inbound(HOUR_START + 42 * MINUTE, 1 * SECOND, business_id=None),
    )
    world.clock.advance(AFTER_THE_HOUR)

    world.record()

    hour = only_hour(world)
    assert hour.hour_start == Microseconds(HOUR_START)
    assert (int(hour.inbound_messages), int(hour.inbound_in_time)) == (6, 3)
    slots = world.slot_repo.list_window(
        ServiceLevelSeries.INBOUND_ANSWERED,
        Microseconds(HOUR_START),
        Microseconds(HOUR_START + HOUR),
    )
    assert len(slots) == 12
    assert [int(slot.total) for slot in slots[:3]] == [1, 1, 1]


def test_an_hour_carries_the_answer_p95_and_the_api_errors() -> None:
    world = SliWorld()
    world.answer(
        *(reply(HOUR_START + index * MINUTE, 2_000) for index in range(19)),
        reply(HOUR_START + 30 * MINUTE, 40_000),
        reply(HOUR_START + 31 * MINUTE, None),  # no measured wait
        reply(HOUR_START + HOUR + MINUTE, 90_000),  # the next hour
    )
    world.slot_repo.add(
        ServiceLevelSeries.API_AVAILABILITY,
        Microseconds(HOUR_START),
        ServiceLevelEventCount(400),
        ServiceLevelEventCount(398),
    )
    world.slot_repo.add(
        ServiceLevelSeries.API_AVAILABILITY,
        Microseconds(HOUR_START),
        ServiceLevelEventCount(100),
        ServiceLevelEventCount(99),
    )
    world.clock.advance(AFTER_THE_HOUR)

    world.record()

    hour = only_hour(world)
    assert int(hour.measured_replies) == 20
    assert hour.reply_p95_ms is not None
    assert 2_000 <= int(hour.reply_p95_ms) < 45_000
    assert (int(hour.api_requests), int(hour.api_server_errors)) == (500, 3)


def test_an_hour_without_replies_has_no_p95() -> None:
    world = SliWorld()
    world.clock.advance(AFTER_THE_HOUR)

    world.record()

    hour = only_hour(world)
    assert hour.reply_p95_ms is None
    assert int(hour.inbound_messages) == 0


def test_a_slot_waits_until_its_messages_had_their_60_s() -> None:
    world = SliWorld()
    world.clock.advance(AFTER_THE_HOUR)  # 71 minutes past HOUR_START
    world.record()
    # The slot from minute 65 to 70 gets a message in its last second.
    world.receive(inbound(HOUR_START + 70 * MINUTE - SECOND, None))

    world.clock.advance(30 * SECOND)
    world.record()
    waiting = world.slot_repo.find_latest(ServiceLevelSeries.INBOUND_ANSWERED)
    world.clock.advance(30 * SECOND)
    world.record()
    judged = world.slot_repo.find_latest(ServiceLevelSeries.INBOUND_ANSWERED)

    assert waiting is not None and judged is not None
    assert int(waiting.slot_start) == HOUR_START + 60 * MINUTE
    assert int(judged.slot_start) == HOUR_START + 65 * MINUTE
    assert (int(judged.total), int(judged.good)) == (1, 0)


def test_a_rerun_writes_nothing_new_and_resumes_after_a_pause() -> None:
    world = SliWorld()
    world.receive(inbound(HOUR_START + MINUTE, 3 * SECOND))
    world.clock.advance(AFTER_THE_HOUR)
    first = world.record()
    assert first == 13 + 1  # the previous hour's slots, one of this hour's

    assert world.record() == 0
    world.clock.advance(3 * HOUR)
    resumed = world.record()

    assert resumed == 3 * 12 + 3
    hours = [int(hour.hour_start) for hour in world.hours.list_all()]
    assert sorted(hours) == [HOUR_START + offset * HOUR for offset in range(4)]
    [first_hour] = [
        hour for hour in world.hours.list_all() if int(hour.hour_start) == HOUR_START
    ]
    assert int(first_hour.inbound_in_time) == 1


def test_old_slots_and_rows_are_removed() -> None:
    world = SliWorld()
    world.clock.advance(AFTER_THE_HOUR)
    world.record()
    world.clock.advance(40 * DAY)

    world.record()

    assert (
        world.slot_repo.list_window(
            ServiceLevelSeries.INBOUND_ANSWERED,
            Microseconds(HOUR_START),
            Microseconds(HOUR_START + 2 * HOUR),
        )
        == []
    )
    assert Microseconds(HOUR_START) in {
        hour.hour_start for hour in world.hours.list_all()
    }

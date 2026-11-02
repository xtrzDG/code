"""The summary job waits an hour, model unasked, while a platform brake holds."""

from datetime import timedelta

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.spend import PlatformBrake
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.memory_helpers import build_summarizer, run_summary_job, summary_jobs
from tests.brain.scripted_turns import say, scripted
from tests.spend_guard.platform_brake_fakes import SetPlatformBrakes

TERRACE_SUMMARY: str = "Asked whether the restaurant has a terrace."
HOUR_MICROSECONDS: int = 60 * 60 * 1_000_000


def quiet_world() -> BrainWorld:
    world = build_world(scripted(say("Yes.")))
    world.send("Hi, do you have a terrace?", name="Giorgi")
    world.clock.advance(timedelta(hours=2))
    return world


@pytest.mark.parametrize("brake", list(PlatformBrake))
def test_a_held_brake_moves_the_summary_an_hour_on(brake: PlatformBrake) -> None:
    world = quiet_world()
    llm = scripted(say(TERRACE_SUMMARY))
    brakes = SetPlatformBrakes(brake)
    summarizer = build_summarizer(world, llm, brakes)
    [queued] = summary_jobs(world)
    now: Microseconds = world.clock.wall_clock().now_unix()

    held = run_summary_job(summarizer, queued)

    [conversation] = world.conversations()
    [_, moved] = summary_jobs(world)
    assert int(held.processed_count) == 0
    assert llm.requests == []
    assert conversation.summary is None
    assert (moved.payload, moved.business_id) == (queued.payload, queued.business_id)
    assert moved.run_at == Microseconds(int(now) + HOUR_MICROSECONDS)

    brakes.brake = None
    world.clock.advance(timedelta(hours=1))
    lifted = run_summary_job(summarizer, moved)

    [conversation] = world.conversations()
    assert int(lifted.processed_count) == 1
    assert str(conversation.summary) == TERRACE_SUMMARY
    assert len(llm.requests) == 1

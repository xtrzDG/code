"""The nightly topic grouping waits while a platform brake holds."""

import pytest

from app.schemas.constants.spend import PlatformBrake
from tests.value.test_conversation_topics import busy_bench, fake_model, tick


@pytest.mark.parametrize("brake", list(PlatformBrake))
def test_a_held_brake_groups_nothing_and_a_lifted_one_groups_at_once(
    brake: PlatformBrake,
) -> None:
    bench = busy_bench()
    llm = fake_model()
    bench.platform_brakes.brake = brake

    held = tick(bench, llm)
    held_topics = bench.topics_repo.get(bench.business.id)
    bench.platform_brakes.brake = None

    assert (held, held_topics, llm.requests) == (0, None, [])
    assert tick(bench, llm) == 1
    assert bench.topics_repo.get(bench.business.id) is not None

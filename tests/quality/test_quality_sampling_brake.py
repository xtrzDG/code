"""The nightly quality judge stays silent while a platform brake holds."""

import pytest

from app.schemas.constants.spend import PlatformBrake
from tests.quality.quality_bench import CountingJudge, QualityBench, tick


@pytest.mark.parametrize("brake", list(PlatformBrake))
def test_a_held_brake_judges_nothing_and_a_lifted_one_judges_again(
    brake: PlatformBrake,
) -> None:
    bench = QualityBench()
    judged = bench.conversation(bench.live_business())
    judge = CountingJudge()
    bench.platform_brakes.brake = brake

    held = bench.job(judge).run(tick(bench))
    bench.platform_brakes.brake = None
    lifted = bench.job(judge).run(tick(bench))

    assert int(held.processed_count) == 0
    assert bench.platform_brakes.readings[0] == bench.now()
    assert int(lifted.processed_count) == 1
    assert [score.conversation_id for score in bench.stored_scores()] == [judged.id]
    assert len(judge.requests) == 1

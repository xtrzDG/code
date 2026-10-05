"""A client's quality trend for the admin and a conversation's score on its card."""

from datetime import timedelta

import pytest

from app.schemas.constants.assistants import JudgeCriterion
from app.schemas.dto.admin import AdminClientQuery
from app.schemas.dto.quality import ConversationQualityQuery
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.quality.get_client_quality_use_case import GetClientQualityUseCase
from app.use_cases.quality.get_conversation_quality_use_case import (
    GetConversationQualityUseCase,
)
from tests.operations.builders import DEFAULT_NOW
from tests.platform_ops.ops_world import ADMIN, AdminsOnly
from tests.quality.quality_bench import CountingJudge, QualityBench, tick, verdict
from tests.value.value_scene import ValueScene


def client_quality(bench: QualityBench) -> GetClientQualityUseCase:
    return GetClientQualityUseCase(
        authorize_platform_admin=AdminsOnly(),
        business_repo=bench.world.business_repo,
        conversation_quality_repo=bench.quality_repo,
        wall_clock=bench.world.clock.wall_clock,
    )


def judge_night(bench: QualityBench, scene: ValueScene, score: int, count: int) -> None:
    """`count` conversations of the scene's business judged at `score`."""

    for _ in range(count):
        bench.conversation(scene.business)

    judge = CountingJudge(
        lambda request: verdict(facts_and_prices=score, handoff=score)
    )
    bench.job(judge).run(tick(bench))


def test_the_admin_sees_the_daily_trend_a_drop_and_the_lowest_scores() -> None:
    bench = QualityBench()
    scene = ValueScene(world=bench.world)
    judge_night(bench, scene, score=5, count=12)
    bench.world.clock.move_to(DEFAULT_NOW + timedelta(days=8))
    judge_night(bench, scene, score=3, count=12)

    view = client_quality(bench).run(
        AdminClientQuery(user_id=ADMIN, business_id=scene.business.id)
    )

    assert len(view.days) == 30
    assert int(view.sample_count) == 24
    assert view.days[-1].average_score is not None
    assert float(view.days[-1].average_score) == 4.2
    assert view.last_week_average is not None
    assert float(view.last_week_average) == 4.2
    assert view.previous_week_average is not None
    assert float(view.previous_week_average) == 5.0
    assert int(view.drop_percent) == 16
    assert view.is_dropping is True
    assert len(view.lowest) == 5
    assert all(float(sample.average_score) == 4.2 for sample in view.lowest)
    criteria = {score.criterion for score in view.lowest[0].scores}
    assert criteria == set(JudgeCriterion)


def test_a_small_sample_is_not_called_a_drop_and_others_are_refused() -> None:
    bench = QualityBench()
    scene = ValueScene(world=bench.world)
    judge_night(bench, scene, score=5, count=3)
    bench.world.clock.move_to(DEFAULT_NOW + timedelta(days=8))
    judge_night(bench, scene, score=2, count=3)
    use_case = client_quality(bench)

    view = use_case.run(AdminClientQuery(user_id=ADMIN, business_id=scene.business.id))

    assert int(view.drop_percent) > 10
    assert view.is_dropping is False
    with pytest.raises(AccessDeniedError):
        use_case.run(AdminClientQuery(user_id=UserId(), business_id=scene.business.id))
    with pytest.raises(NotFoundError):
        use_case.run(AdminClientQuery(user_id=ADMIN, business_id=BusinessId()))


def test_a_member_reads_a_conversations_score_and_its_notes() -> None:
    bench = QualityBench()
    scene = ValueScene(world=bench.world)
    judged = bench.conversation(scene.business)
    bench.job(
        CountingJudge(
            lambda request: verdict(["Did not confirm the time"], booking_data=2)
        )
    ).run(tick(bench))
    unjudged = bench.conversation(scene.business)
    use_case = GetConversationQualityUseCase(
        authorize_business_access=bench.world.authorize(),
        conversation_quality_repo=bench.quality_repo,
    )

    view = use_case.run(
        ConversationQualityQuery(
            user_id=scene.owner.id,
            business_id=scene.business.id,
            conversation_id=judged.id,
        )
    )
    empty = use_case.run(
        ConversationQualityQuery(
            user_id=scene.owner.id,
            business_id=scene.business.id,
            conversation_id=unjudged.id,
        )
    )

    assert view.score is not None
    assert float(view.score.average_score) == 4.4
    assert [str(note) for note in view.score.judge_notes] == [
        "Did not confirm the time"
    ]
    assert empty.score is None
    with pytest.raises(NotFoundError):
        use_case.run(
            ConversationQualityQuery(
                user_id=UserId(),
                business_id=scene.business.id,
                conversation_id=judged.id,
            )
        )

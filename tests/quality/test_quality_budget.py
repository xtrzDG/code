"""The nightly quality judge stops at QUALITY_SAMPLE_BUDGET_CENTS (cost cap)."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.quality.constrained_integers import (
    ConversationQualityHundredths,
)
from app.utilities.quality.quality_sampling import quality_score_id_of
from tests.assembly.judge_helpers import scores
from tests.quality.quality_bench import CountingJudge, QualityBench, tick


def spent_earlier_today(bench: QualityBench, cost: int) -> None:
    """A score the night's run already paid for (another business)."""

    business = bench.live_business()
    conversation_id = ConversationId()
    bench.quality_repo.save(
        ConversationQualityScoreDocument(
            id=quality_score_id_of(conversation_id),
            business_id=business.id,
            conversation_id=conversation_id,
            assistant_version_id=AssistantVersionId(),
            channel=ChannelKind.WHATSAPP,
            scores=scores(),
            score_hundredths=ConversationQualityHundredths(500),
            judge_model_id=LlmModelId("gpt-5-mini"),
            cost_micro_usd=CostMicroUsd(cost),
            judged_at=bench.now(),
            created_at=bench.now(),
            updated_at=bench.now(),
        )
    )


def test_the_night_stops_before_a_call_could_pass_the_budget() -> None:
    bench = QualityBench()
    business = bench.live_business()
    for _ in range(4):
        bench.conversation(business)
    # Each call costs 10 200 micro-dollars; its worst case (16 000 output
    # tokens) about 16 300. Three cents allow two calls, not a third.
    judge = CountingJudge()

    report = bench.job(judge, budget_cents=3).run(tick(bench))

    assert int(report.processed_count) == 2
    assert len(judge.requests) == 2
    assert sum(int(score.cost_micro_usd) for score in bench.stored_scores()) == 20_400


def test_what_the_day_already_spent_counts_against_the_budget() -> None:
    bench = QualityBench()
    spent_earlier_today(bench, cost=20_000)
    bench.conversation(bench.live_business())
    judge = CountingJudge()

    report = bench.job(judge, budget_cents=3).run(tick(bench))

    assert int(report.processed_count) == 0
    assert judge.requests == []


def test_a_zero_budget_turns_the_sampling_off() -> None:
    bench = QualityBench()
    bench.conversation(bench.live_business())
    judge = CountingJudge()

    report = bench.job(judge, budget_cents=0).run(tick(bench))

    assert int(report.processed_count) == 0
    assert judge.requests == []

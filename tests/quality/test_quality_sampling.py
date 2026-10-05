"""Which real conversations the nightly quality job judges, and what it stores."""

from datetime import timedelta

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.dto.conversations import LlmRequest
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.quality.constrained_integers import QualitySamplePercent
from app.utilities.quality.quality_sampling import is_sampled, quality_score_id_of
from tests.operations.builders import DEFAULT_NOW
from tests.quality.quality_bench import CountingJudge, QualityBench, tick, verdict


def request_text(request: LlmRequest) -> str:
    return str(request.transcript[0])


def test_the_judge_scores_quiet_real_conversations_of_live_businesses() -> None:
    bench = QualityBench()
    business = bench.live_business()
    judged = bench.conversation(business)
    paused = bench.conversation(bench.live_business(BusinessStatus.PAUSED))
    bench.conversation(bench.live_business(BusinessStatus.TESTING))
    bench.conversation(business, hours_ago=0.5)  # still going on
    bench.conversation(business, hours_ago=50)  # older than two days
    bench.conversation(business, is_sandbox=True)
    bench.conversation(business, texts=("Hello?",))  # never answered
    judge = CountingJudge(
        lambda request: verdict(["Price not confirmed"], facts_and_prices=3)
    )

    report = bench.job(judge).run(tick(bench))

    assert int(report.processed_count) == 2
    stored = {score.conversation_id: score for score in bench.stored_scores()}
    assert set(stored) == {judged.id, paused.id}
    score = stored[judged.id]
    assert score.id == quality_score_id_of(judged.id)
    assert int(score.score_hundredths) == 460
    assert [str(note) for note in score.judge_notes] == ["Price not confirmed"]
    assert score.channel is judged.channel
    assert score.assistant_version_id == judged.assistant_version_id
    assert int(score.cost_micro_usd) == 10_200
    assert score.judged_at == bench.now()


def test_a_conversation_is_judged_once_and_the_sample_is_stable() -> None:
    bench = QualityBench()
    business = bench.live_business()
    conversations = [bench.conversation(business) for _ in range(40)]
    judge = CountingJudge()

    first = bench.job(judge, percent=25).run(tick(bench))
    second = bench.job(judge, percent=25).run(tick(bench))

    picked = {score.conversation_id for score in bench.stored_scores()}
    assert picked == {
        conversation.id
        for conversation in conversations
        if is_sampled(conversation.id, QualitySamplePercent(25))
    }
    assert 0 < len(picked) < len(conversations)
    assert int(first.processed_count) == len(picked)
    assert int(second.processed_count) == 0
    assert len(judge.requests) == len(picked)


def test_each_business_is_capped_and_businesses_take_turns() -> None:
    bench = QualityBench()
    busy = bench.live_business()
    quiet = bench.live_business()
    for _ in range(5):
        bench.conversation(busy)
    lone = bench.conversation(quiet)
    judge = CountingJudge()

    bench.job(judge, per_business=3).run(tick(bench))

    judged = [score.business_id for score in bench.stored_scores()]
    assert judged.count(busy.id) == 3
    assert judged.count(quiet.id) == 1
    assert any(lone.id == score.conversation_id for score in bench.stored_scores())


def test_contacts_are_blanked_before_the_judge_and_in_its_notes() -> None:
    bench = QualityBench()
    business = bench.live_business()
    bench.conversation(
        business,
        texts=(
            "Call me on +995 555 12 34 56 or write to nino@example.com",
            "Thank you, we will call you.",
        ),
    )
    judge = CountingJudge(
        lambda request: verdict(["It promised to call +995 555 12 34 56"])
    )

    bench.job(judge).run(tick(bench))

    sent = request_text(judge.requests[0])
    assert "555 12 34 56" not in sent
    assert "nino@example.com" not in sent
    assert "[phone]" in sent
    assert "[e-mail]" in sent
    (score,) = bench.stored_scores()
    assert [str(note) for note in score.judge_notes] == ["It promised to call [phone]"]


def test_an_unreadable_answer_stores_nothing_and_a_failing_call_is_skipped() -> None:
    bench = QualityBench()
    business = bench.live_business()
    bench.conversation(business)
    bench.conversation(business)
    answers = iter(["not json at all"])

    def answer(request: LlmRequest) -> str:
        del request
        text = next(answers, None)
        if text is None:
            raise ExternalServiceError("The judge is down.")
        return text

    report = bench.job(CountingJudge(answer)).run(tick(bench))

    assert int(report.processed_count) == 0
    assert bench.stored_scores() == []


def test_nothing_is_judged_when_sampling_is_off_and_old_scores_are_purged() -> None:
    bench = QualityBench()
    business = bench.live_business()
    old = bench.conversation(business)
    judge = CountingJudge()
    bench.job(judge).run(tick(bench))
    assert len(bench.stored_scores()) == 1
    bench.conversation(business)
    bench.world.clock.move_to(DEFAULT_NOW + timedelta(days=91))

    off = bench.job(judge, percent=0).run(tick(bench))

    assert int(off.processed_count) == 0
    assert bench.stored_scores() == []
    assert bench.quality_repo.get(business.id, old.id) is None

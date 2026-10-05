"""
Whose conversations the nightly judge may read: a business that turned the
sample off in Settings → Privacy is never sampled, and the judge is the
assistant's own model unless QUALITY_SAMPLING_JUDGE_SAME_PROVIDER is off.
"""

from app.schemas.dto.conversations import LlmRequest
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from tests.quality.quality_bench import CountingJudge, QualityBench, tick, verdict


def test_a_business_that_turned_the_sample_off_is_never_read() -> None:
    bench = QualityBench()
    sampled = bench.live_business()
    private = bench.live_business()
    settings = bench.privacy_settings_repo.get_or_default(private.id)
    settings.quality_sampling_allowed = False
    bench.privacy_settings_repo.save(settings)
    kept = bench.conversation(sampled)
    bench.conversation(private)
    read: list[str] = []

    def answer(request: LlmRequest) -> str:
        read.append(str(request.transcript[0]))
        return verdict()

    report = bench.job(CountingJudge(answer)).run(tick(bench))

    assert int(report.processed_count) == 1
    assert [score.conversation_id for score in bench.stored_scores()] == [kept.id]
    assert len(read) == 1


def test_the_judge_is_the_assistants_own_model_by_default() -> None:
    bench = QualityBench()
    bench.world.settings = bench.world.settings.model_copy(
        update={"llm_judge_model_id": LlmModelId("claude-sonnet-5-5")}
    )
    first = bench.conversation(bench.live_business())
    models: list[LlmModelId] = []

    def answer(request: LlmRequest) -> str:
        models.append(request.model_id)
        return verdict()

    bench.job(CountingJudge(answer)).run(tick(bench))
    second = bench.conversation(bench.live_business())
    bench.job(CountingJudge(answer), judge_same_provider=False).run(tick(bench))

    assert models == [LlmModelId("gpt-5-mini"), LlmModelId("claude-sonnet-5-5")]
    judges = {
        score.conversation_id: str(score.judge_model_id)
        for score in bench.stored_scores()
    }
    assert judges == {first.id: "gpt-5-mini", second.id: "claude-sonnet-5-5"}

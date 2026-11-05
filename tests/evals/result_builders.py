"""Builders of run results for the summary, baseline and report tests."""

from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.evaluations import EvalCriterionResult
from scripts.eval_harness.run_results import JudgeResult, SampleResult, ScenarioResult


def sample(
    passed: bool,
    latencies: list[int] | None = None,
    cost: int = 0,
    judge: dict[str, int] | None = None,
    stale: bool = False,
    error: str | None = None,
) -> SampleResult:
    return SampleResult(
        sample_index=0,
        is_passed=passed,
        criteria=[
            EvalCriterionResult(criterion=EvalCriterion.LANGUAGE, is_passed=True),
            EvalCriterionResult(criterion=EvalCriterion.PRICES, is_passed=passed),
        ],
        judge=None if judge is None else JudgeResult(scores=judge),
        cost_micro_usd=cost,
        turn_latencies_ms=latencies or [],
        stale_reasons=["changed"] if stale else [],
        error=error,
    )


def scenario(niche: str, language: str, samples: list[SampleResult]) -> ScenarioResult:
    return ScenarioResult(
        niche=niche,
        scenario_id=f"price__{language}",
        language=language,
        kind="price_question",
        samples=samples,
    )

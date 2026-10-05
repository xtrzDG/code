from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.assistants import AutotestOutcome, AutotestRunStatus
from app.schemas.domain.assistants import AutotestRunDocument, AutotestScenarioResult
from app.schemas.dto.assistants.assistant_views import (
    AutotestRunView,
    AutotestScenarioResultView,
    AutotestTranscriptLineView,
    JudgeCriterionScoreView,
    OwnerCheckAskedView,
)
from app.schemas.dto.assistants.autotest_runs import AutotestRunViewSource
from app.schemas.typings.assistants.constrained_integers import AutotestScenarioCount
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.utilities.assembly.autotest_comparison import compare_runs
from app.utilities.assembly.autotest_evaluation import count_run_scenarios


class AutotestRunViewTransformer(
    TransformerContract[AutotestRunViewSource, AutotestRunView]
):
    """
    A stored autotest run with counts, total cost and its version's status,
    and, once it finished, how it compares with the live version's run.
    """

    def transform(self, input_data: AutotestRunViewSource) -> AutotestRunView:
        run: AutotestRunDocument = input_data.run
        return AutotestRunView(
            id=run.id,
            business_id=run.business_id,
            assistant_version_id=run.assistant_version_id,
            status=run.status,
            is_full_coverage=run.is_full_coverage,
            version_status=input_data.version.status,
            scenario_count=count_run_scenarios(run),
            passed_count=AutotestScenarioCount(
                sum(
                    1
                    for result in run.results
                    if result.outcome is AutotestOutcome.PASSED
                )
            ),
            pass_rate=run.pass_rate,
            average_score=run.average_score,
            is_passed=run.is_passed,
            cost_micro_usd=CostMicroUsd(
                sum(int(result.cost_micro_usd) for result in run.results)
            ),
            results=[self._build_result_view(result) for result in run.results],
            comparison=(
                compare_runs(run, input_data.baseline_run, input_data.baseline_version)
                if run.status is AutotestRunStatus.FINISHED
                and input_data.baseline_run is not None
                and input_data.baseline_version is not None
                else None
            ),
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    def _build_result_view(
        self,
        result: AutotestScenarioResult,
    ) -> AutotestScenarioResultView:
        return AutotestScenarioResultView(
            scenario_key=result.scenario_key,
            kind=result.kind,
            language=result.language,
            outcome=result.outcome,
            scores=[
                JudgeCriterionScoreView(criterion=score.criterion, score=score.score)
                for score in result.scores
            ],
            judge_notes=list(result.judge_notes),
            check_notes=list(result.check_notes),
            check_codes=list(result.check_codes),
            transcript=[
                AutotestTranscriptLineView(author=line.author, text=line.text)
                for line in result.transcript
            ],
            cost_micro_usd=result.cost_micro_usd,
            autotest_case_id=result.autotest_case_id,
            sample_count=result.sample_count,
            passed_sample_count=result.passed_sample_count,
            owner_check=(
                None
                if result.owner_check is None
                else OwnerCheckAskedView(
                    question=result.owner_check.question,
                    expectation=result.owner_check.expectation,
                    expected_text=result.owner_check.expected_text,
                )
            ),
            conversation_id=result.conversation_id,
            answer_message_id=result.answer_message_id,
        )

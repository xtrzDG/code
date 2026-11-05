"""
The platform admin reads the active version's own autotest verdict: a run
that passed with a scenario failed is a passed run (as on the version
page), and why a scenario failed comes as codes, not English text.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestCheckCode,
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.client_health import ClientHealthIssue
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
    AutotestScenarioResult,
    JudgeCriterionScore,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.admin import (
    AdminClientQuery,
    AdminClientSummary,
    ClientSummarySource,
)
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    JudgeScore,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import AutotestCheckNote, SystemPromptText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_evaluation import build_verdict, summarize_run
from tests.billing.admin_world import AdminWorld, build_admin_world


def result(key: str, scores: dict[JudgeCriterion, int]) -> AutotestScenarioResult:
    is_failed: bool = any(score < 3 for score in scores.values())
    return AutotestScenarioResult(
        scenario_key=AutotestScenarioKey(key),
        kind=AutotestScenarioKind.RUDE_CUSTOMER,
        language=LanguageTag("ar"),
        outcome=AutotestOutcome.FAILED if is_failed else AutotestOutcome.PASSED,
        scores=[
            JudgeCriterionScore(criterion=criterion, score=JudgeScore(score))
            for criterion, score in scores.items()
        ],
        check_notes=(
            [AutotestCheckNote("Reply 1 is not written in Arabic (ar).")]
            if is_failed
            else []
        ),
        check_codes=[AutotestCheckCode.WRONG_REPLY_LANGUAGE] if is_failed else [],
    )


def version(
    world: AdminWorld,
    business: BusinessDocument,
    number: int,
    status: AssistantVersionStatus,
) -> AssistantVersionDocument:
    return AssistantVersionDocument(
        business_id=business.id,
        version_number=AssistantVersionNumber(number),
        status=status,
        niche_key=NicheKey.RESTAURANT,
        model_id=LlmModelId("gpt-5-mini"),
        prompt_text=SystemPromptText("You are the AI assistant."),
        tools=[AssistantToolName.CREATE_BOOKING],
        languages=[LanguageTag("ka")],
        default_language=LanguageTag("ka"),
        is_voice_enabled=False,
        facts=[],
        profile_revision=world.testbed.clock.now(),
    )


def publish(
    world: AdminWorld, business: BusinessDocument, published_id: AssistantVersionId
) -> None:
    stored = world.testbed.business(business.id)
    stored.published_assistant_version_id = published_id
    world.testbed.business_repo.save(stored)


def publish_tested_version(world: AdminWorld) -> AssistantVersionDocument:
    """The Italian client goes live with v3: 4 of 5 scenarios passed, run passed."""

    business = world.italian
    good = {criterion: 5 for criterion in JudgeCriterion}
    results = [result(f"price__it__{index}", good) for index in range(4)]
    results.append(
        result(
            "rude_customer__ar",
            good | {JudgeCriterion.LANGUAGE: 1, JudgeCriterion.HANDOFF: 2},
        )
    )
    summary = summarize_run(results)
    live = version(world, business, 3, AssistantVersionStatus.PUBLISHED)
    run = AutotestRunDocument(
        business_id=business.id,
        assistant_version_id=live.id,
        is_full_coverage=True,
        results=results,
        pass_rate=summary.pass_rate,
        average_score=summary.average_score,
        is_passed=summary.is_passed,
    )
    live.autotest_run_id = run.id
    live.autotest_verdict = build_verdict(run, Microseconds(1))
    world.testbed.autotest_run_repo.save(run)
    world.testbed.assistant_version_repo.save(live)
    publish(world, business, live.id)
    return live


def italian_summary(world: AdminWorld) -> AdminClientSummary:
    return world.testbed.summarize_client.run(
        ClientSummarySource(business=world.testbed.business(world.italian.id))
    )


def test_a_passed_run_with_a_failed_scenario_is_not_an_issue() -> None:
    world = build_admin_world()
    publish_tested_version(world)

    summary = italian_summary(world)

    verdict = summary.autotest_verdict
    assert verdict is not None
    assert verdict.is_passed is True
    assert (int(verdict.passed_count or 0), int(verdict.scenario_count or 0)) == (4, 5)
    assert int(verdict.version_number) == 3
    assert int(summary.failed_tests) == 1
    assert ClientHealthIssue.AUTOTESTS_FAILED not in summary.health_issues
    assert ClientHealthIssue.NOT_PUBLISHED not in summary.health_issues


def test_failed_scenarios_explain_themselves_with_codes() -> None:
    world = build_admin_world()
    publish_tested_version(world)

    health = world.testbed.get_client_health.run(
        AdminClientQuery(user_id=world.admin.id, business_id=world.italian.id)
    )

    [failed] = health.failed_autotests
    assert str(failed.scenario_key) == "rude_customer__ar"
    assert failed.check_codes == [AutotestCheckCode.WRONG_REPLY_LANGUAGE]
    assert failed.low_criteria == [JudgeCriterion.HANDOFF, JudgeCriterion.LANGUAGE]


def test_a_version_tested_before_verdicts_reads_its_status() -> None:
    world = build_admin_world()
    legacy = version(world, world.italian, 1, AssistantVersionStatus.TESTS_FAILED)
    legacy.test_score = AverageJudgeScore(3.1)
    world.testbed.assistant_version_repo.save(legacy)

    summary = italian_summary(world)

    verdict = summary.autotest_verdict
    assert verdict is not None
    assert (verdict.is_passed, verdict.passed_count, verdict.scenario_count) == (
        False,
        None,
        None,
    )
    assert int(summary.failed_tests) == 0
    assert ClientHealthIssue.AUTOTESTS_FAILED in summary.health_issues


def test_an_untested_client_has_no_verdict() -> None:
    world = build_admin_world()
    world.testbed.assistant_version_repo.save(
        version(world, world.italian, 1, AssistantVersionStatus.DRAFT)
    )

    summary = italian_summary(world)

    assert summary.autotest_verdict is None
    assert summary.last_test_score is None
    assert ClientHealthIssue.AUTOTESTS_FAILED not in summary.health_issues

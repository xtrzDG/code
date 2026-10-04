"""
The owner's checks in autotest runs: planned after the other scenarios (all
of them in a quick check), played with their question word for word and
decided by their expectation instead of the judge.
"""

from app.schemas.constants.assistants import (
    AutotestCheckCode,
    AutotestExpectation,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.autotest_runs import (
    AutotestPlanningRequest,
    AutotestScenario,
)
from app.schemas.dto.assistants.smoke_checks import (
    SmokeCheckSelection,
    SmokeScenarioPick,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.autotests.plan_autotest_scenarios_use_case import (
    PlanAutotestScenariosUseCase,
)
from app.utilities.assembly.autotest_prompts import OWNER_CHECK_CONTINUATION_OPENING
from app.utilities.assembly.owner_check_scenarios import owner_check_key
from tests.assembly.autotest_run_helpers import run_one, start
from tests.assembly.autotest_scripts import DONE, build_reply
from tests.assembly.llm_request_helpers import read_last_user_text
from tests.assembly.testbed import AssemblyTestbed

CAKE: str = "Можно прийти со своим тортом?"


def save_case(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    expectation: AutotestExpectation,
    expected_text: str | None = None,
    language: str = "ru",
    question: str = CAKE,
    is_active: bool = True,
) -> AutotestCaseDocument:
    case = AutotestCaseDocument(
        business_id=business.id,
        question=AutotestCaseQuestion(question),
        expectation=expectation,
        expected_text=None
        if expected_text is None
        else AutotestExpectedText(expected_text),
        language=LanguageTag(language),
        is_active=is_active,
    )
    testbed.autotest_case_repo.save(case)
    return case


def planner(testbed: AssemblyTestbed) -> PlanAutotestScenariosUseCase:
    return PlanAutotestScenariosUseCase(
        business_profile_repo=testbed.profile_repo,
        knowledge_item_repo=testbed.knowledge_repo,
        resource_repo=testbed.resource_repo,
        autotest_case_repo=testbed.autotest_case_repo,
        niche_template_registry=testbed.niche_registry,
        language_registry=testbed.language_registry,
    )


def owner_scenarios(scenarios: list[AutotestScenario]) -> list[AutotestScenario]:
    return [s for s in scenarios if s.kind is AutotestScenarioKind.OWNER_CHECK]


def stored_version(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    version_id: AssistantVersionId,
) -> AssistantVersionDocument:
    version = testbed.version_repo.get(business.id, version_id)
    assert version is not None
    return version


def test_a_full_run_ends_with_the_active_checks_in_its_languages() -> None:
    testbed = AssemblyTestbed()
    business, details = start(testbed)
    version = stored_version(testbed, business, details.id)
    russian = save_case(testbed, business, AutotestExpectation.MUST_HAND_OFF)
    save_case(testbed, business, AutotestExpectation.MUST_HAND_OFF, language="en")
    save_case(
        testbed, business, AutotestExpectation.MUST_HAND_OFF, "x", is_active=False
    )

    planned = planner(testbed).run(
        AutotestPlanningRequest(
            business=business, version=version, languages=[LanguageTag("ru")]
        )
    )

    checks = owner_scenarios(planned.scenarios)
    assert planned.scenarios[-1] == checks[-1]
    assert [scenario.key for scenario in checks] == [owner_check_key(russian.id)]
    assert checks[0].owner_check is not None
    assert checks[0].owner_check.question == CAKE
    assert checks[0].language_name == "Russian"
    assert CAKE in str(checks[0].goal)


def test_kinds_without_owner_checks_leave_them_out() -> None:
    testbed = AssemblyTestbed()
    business, details = start(testbed)
    version = stored_version(testbed, business, details.id)
    save_case(testbed, business, AutotestExpectation.MUST_HAND_OFF)

    others = planner(testbed).run(
        AutotestPlanningRequest(
            business=business,
            version=version,
            kinds=[AutotestScenarioKind.HUMAN_REQUEST],
        )
    )
    only = planner(testbed).run(
        AutotestPlanningRequest(
            business=business,
            version=version,
            kinds=[AutotestScenarioKind.OWNER_CHECK],
        )
    )

    assert owner_scenarios(others.scenarios) == []
    assert [scenario.kind for scenario in only.scenarios] == [
        AutotestScenarioKind.OWNER_CHECK
    ]
    assert only.is_full_coverage is False


def test_a_quick_check_plays_every_active_check() -> None:
    testbed = AssemblyTestbed()
    business, details = start(testbed)
    version = stored_version(testbed, business, details.id)
    save_case(testbed, business, AutotestExpectation.MUST_HAND_OFF)
    save_case(
        testbed,
        business,
        AutotestExpectation.MUST_HAND_OFF,
        language="he",
        question="אפשר להביא עוגה?",
    )

    planned = planner(testbed).run(
        AutotestPlanningRequest(
            business=business,
            version=version,
            smoke_check=SmokeCheckSelection(
                picks=[
                    SmokeScenarioPick(
                        kind=AutotestScenarioKind.HUMAN_REQUEST,
                        language=LanguageTag("ka"),
                    )
                ],
                price_language=LanguageTag("ka"),
            ),
        )
    )

    checks = owner_scenarios(planned.scenarios)
    assert [str(scenario.language) for scenario in checks] == ["ru", "he"]
    assert str(checks[1].language_name) in ("Hebrew", "he")
    assert planned.is_full_coverage is False


def test_a_check_asks_its_question_and_skips_the_judge() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    case = save_case(
        testbed, business, AutotestExpectation.MUST_MENTION, "своим тортом"
    )
    testbed.reply_scripts[owner_check_key(case.id)] = lambda message, key, turn: (
        build_reply("ru", text="Да, со своим тортом можно.")
    )

    run = run_one(testbed, business, version, "ru", AutotestScenarioKind.OWNER_CHECK)

    result = run.results[0]
    assert result.outcome is AutotestOutcome.PASSED
    assert result.autotest_case_id == case.id
    assert result.scores == []
    assert [(line.author, str(line.text)) for line in result.transcript] == [
        (MessageAuthor.CUSTOMER, CAKE),
        (MessageAuthor.ASSISTANT, "Да, со своим тортом можно."),
    ]
    assert testbed.customer_requests.requests == []
    assert testbed.judge_requests.requests == []


def test_a_check_whose_answer_misses_the_text_fails_with_its_code() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    case = save_case(
        testbed, business, AutotestExpectation.MUST_MENTION, "своим тортом"
    )
    testbed.reply_scripts[owner_check_key(case.id)] = lambda message, key, turn: (
        build_reply("ru", text="Нет, нельзя.")
    )

    run = run_one(testbed, business, version, "ru", AutotestScenarioKind.OWNER_CHECK)

    result = run.results[0]
    assert result.outcome is AutotestOutcome.FAILED
    assert result.autotest_case_id == case.id
    assert result.check_codes == [AutotestCheckCode.EXPECTED_TEXT_MISSING]


def test_a_request_check_goes_on_with_the_ai_customer() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    case = save_case(testbed, business, AutotestExpectation.MUST_CREATE_LEAD)
    testbed.customer_script = lambda request, turn: (
        DONE if turn >= 1 else "Нино, +995 555 12 34 56"
    )

    def reply(message: InboundMessage, key: str, turn: int) -> AssistantReply:
        return build_reply("ru", is_lead_created=turn >= 1)

    testbed.reply_scripts[owner_check_key(case.id)] = reply

    run = run_one(testbed, business, version, "ru", AutotestScenarioKind.OWNER_CHECK)

    result = run.results[0]
    assert result.outcome is AutotestOutcome.PASSED
    assert [str(line.text) for line in result.transcript][0] == CAKE
    first_customer_turn = read_last_user_text(testbed.customer_requests.requests[0])
    assert first_customer_turn.startswith(OWNER_CHECK_CONTINUATION_OPENING)
    assert f"Your first message: {CAKE}" in first_customer_turn
    assert testbed.judge_requests.requests == []

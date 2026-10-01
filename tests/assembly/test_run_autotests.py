import pytest

from app.gateways.worker.background_worker import BackgroundWorker
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.assistants.run_queued_autotests_orchestrator import (
    RunQueuedAutotestsOrchestrator,
)
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestRunStatus,
    AutotestScenarioKind,
    LlmEffort,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants import (
    AssistantVersionDetails,
    AssistantVersionQuery,
    AutotestRunCompletion,
    AutotestRunView,
    AutotestScenarioResultView,
    LlmTokenPrice,
    RunAutotestsCommand,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage, LlmRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.assembly.builders import (
    seed_georgian_restaurant,
    seed_israeli_clinic,
    seed_japanese_restaurant,
    seed_online_shop,
)
from tests.assembly.fakes import read_last_user_text
from tests.assembly.testbed import (
    CUSTOMER_TEXTS,
    DONE,
    AssemblyTestbed,
    build_reply,
)

GEORGIAN_SCENARIO_COUNT: int = 3 * 9 + 2


def start(
    testbed: AssemblyTestbed,
    seed: BusinessDocument | None = None,
) -> tuple[BusinessDocument, AssistantVersionDetails]:
    business = seed or seed_georgian_restaurant(testbed)
    return business, testbed.assemble(business.id)


def results_by_key(run: AutotestRunView) -> dict[str, AutotestScenarioResultView]:
    return {str(result.scenario_key): result for result in run.results}


def run_one(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    version: AssistantVersionDetails,
    language: str,
    kind: AutotestScenarioKind,
) -> AutotestRunView:
    testbed.advance(60)
    return testbed.run_autotests_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
            languages=[LanguageTag(language)],
            kinds=[kind],
        )
    )


def test_all_scenarios_pass_and_the_version_becomes_ready() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    default_script = testbed.customer_script

    def slow_customer(request: LlmRequest, turn_index: int) -> str:
        testbed.advance(1)
        return default_script(request, turn_index)

    testbed.customer_script = slow_customer

    run = testbed.run_autotests(business.id, version.id)

    assert run.scenario_count == GEORGIAN_SCENARIO_COUNT
    assert run.passed_count == GEORGIAN_SCENARIO_COUNT
    assert float(run.pass_rate) == 1.0
    assert run.average_score is not None
    assert float(run.average_score) == 5.0
    assert run.is_passed is True
    assert run.version_status is AssistantVersionStatus.READY
    stored_version = testbed.version(business.id, version.id)
    assert stored_version.status is AssistantVersionStatus.READY
    assert stored_version.test_score is not None
    assert float(stored_version.test_score) == 5.0
    assert stored_version.autotest_run_id == run.id
    stored_run = testbed.run_repo.get(business.id, run.id)
    assert stored_run is not None
    assert stored_run.assistant_version_id == version.id
    assert run.created_at < run.updated_at
    keys = set(results_by_key(run))
    assert {
        "booking__ka",
        "booking_out_of_hours__ru",
        "prompt_injection__en",
        "price_question__ka__1",
        "price_question__ru__2",
    } <= keys
    assert all(
        [line.author for line in result.transcript]
        == [MessageAuthor.CUSTOMER, MessageAuthor.ASSISTANT]
        for result in run.results
    )
    assert all(result.judge_notes for result in run.results)


def test_sandbox_messages_are_pinned_to_the_version_under_test() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    testbed.run_autotests(business.id, version.id)

    messages: list[InboundMessage] = testbed.conversation.inbound_messages
    assert len(messages) == GEORGIAN_SCENARIO_COUNT
    assert all(message.is_sandbox for message in messages)
    assert all(message.channel is ChannelKind.OWNER_TEST for message in messages)
    assert all(message.assistant_version_id == version.id for message in messages)
    assert all(message.business_id == business.id for message in messages)
    assert len({str(message.channel_user_id) for message in messages}) == len(messages)
    georgian_texts = [
        str(message.text)
        for message in messages
        if str(message.channel_user_id).endswith("__ka")
    ]
    assert georgian_texts and set(georgian_texts) == {CUSTOMER_TEXTS["ka"]}


def test_each_run_uses_new_channel_users() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    testbed.run_autotests(business.id, version.id)
    testbed.run_autotests(business.id, version.id)

    channel_users = [
        str(message.channel_user_id)
        for message in testbed.conversation.inbound_messages
    ]
    assert len(set(channel_users)) == 2 * GEORGIAN_SCENARIO_COUNT


def test_ai_customer_and_judge_use_the_judge_model_without_tools() -> None:
    testbed = AssemblyTestbed(environment={"LLM_JUDGE_EFFORT": "high"})
    business, version = start(testbed)

    run_one(testbed, business, version, "ru", AutotestScenarioKind.HUMAN_REQUEST)

    customer_requests: list[LlmRequest] = testbed.customer_requests.requests
    judge_requests: list[LlmRequest] = testbed.judge_requests.requests
    assert len(customer_requests) == 2
    assert len(judge_requests) == 1
    for request in [*customer_requests, *judge_requests]:
        assert request.model_id == testbed.settings.llm_judge_model_id
        assert request.effort is LlmEffort.HIGH
        assert request.tools == []

    persona = str(customer_requests[0].system_prompt)
    assert "only in Russian (language tag ru)" in persona
    assert "Your goal: Ask to talk to a human employee right away." in persona
    assert "Your phone number is +995 555 12 34 56." in persona
    assert "- Opening hours on Friday: 12:00–15:00, 18:00–24:00" in persona
    assert "[DONE]" in persona
    judge_prompt = str(judge_requests[0].system_prompt)
    for criterion in (
        "facts_and_prices",
        "booking_data",
        "ai_disclosure",
        "handoff",
        "language",
    ):
        assert f"- {criterion}:" in judge_prompt

    judge_input = read_last_user_text(judge_requests[0])
    assert judge_input.startswith("Scenario: human_request__ru (human_request)\n")
    assert "- handed off to a human: yes" in judge_input
    assert "- Business name: Café Rustaveli" in judge_input
    assert f"Customer: {CUSTOMER_TEXTS['ru']}" in judge_input
    assert "Assistant: Здравствуйте! Я AI-ассистент." in judge_input


def test_ai_customer_sees_the_assistant_replies() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    run_one(testbed, business, version, "en", AutotestScenarioKind.UNKNOWN_QUESTION)

    second_request = testbed.customer_requests.requests[1]
    assert len(second_request.transcript) == 3
    assert read_last_user_text(second_request) == (
        "Hello! I am the AI assistant. How can I help?"
    )


def test_conversation_stops_at_the_turn_limit() -> None:
    testbed = AssemblyTestbed(environment={"AUTOTEST_TURN_LIMIT": "3"})
    business, version = start(testbed)
    testbed.customer_script = lambda request, turn: f"Message {turn + 1}"

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.RUDE_CUSTOMER)

    result = run.results[0]
    assert [str(line.text) for line in result.transcript[::2]] == [
        "Message 1",
        "Message 2",
        "Message 3",
    ]
    assert len(testbed.conversation.inbound_messages) == 3
    assert len(testbed.customer_requests.requests) == 3


def test_done_marker_ends_the_conversation_without_sending_it() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.customer_script = lambda request, turn: (
        "Hello" if turn == 0 else "Thanks, bye! [DONE]"
    )

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.RUDE_CUSTOMER)

    assert [str(message.text) for message in testbed.conversation.inbound_messages] == [
        "Hello"
    ]
    assert run.results[0].outcome is AutotestOutcome.PASSED


def test_customer_who_writes_nothing_errors_the_scenario() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.customer_script = lambda request, turn: DONE

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.RUDE_CUSTOMER)

    result = run.results[0]
    assert result.outcome is AutotestOutcome.ERRORED
    assert result.check_notes == ["The AI customer wrote no message."]
    assert result.scores == []
    assert testbed.judge_requests.requests == []


def test_one_failed_price_scenario_blocks_ready() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_scores["price_question__ru__2"] = {
        "facts_and_prices": 2,
        "booking_data": 5,
        "ai_disclosure": 5,
        "handoff": 5,
        "language": 5,
    }

    run = testbed.run_autotests(business.id, version.id)

    results = results_by_key(run)
    assert results["price_question__ru__2"].outcome is AutotestOutcome.FAILED
    assert run.passed_count == GEORGIAN_SCENARIO_COUNT - 1
    assert run.average_score is not None
    assert float(run.average_score) > 4.0
    assert run.is_passed is False
    assert run.version_status is AssistantVersionStatus.TESTS_FAILED
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.TESTS_FAILED
    )


def test_average_below_four_blocks_ready_even_if_every_scenario_passed() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    low_but_passing = {
        "facts_and_prices": 4,
        "booking_data": 4,
        "ai_disclosure": 4,
        "handoff": 3,
        "language": 4,
    }
    for language in ("ka", "ru", "en"):
        for kind in AutotestScenarioKind:
            testbed.judge_scores[f"{kind.value}__{language}"] = low_but_passing

    testbed.judge_scores["price_question__ka__1"] = low_but_passing
    testbed.judge_scores["price_question__ru__2"] = low_but_passing

    run = testbed.run_autotests(business.id, version.id)

    assert run.passed_count == GEORGIAN_SCENARIO_COUNT
    assert run.average_score is not None
    assert float(run.average_score) == pytest.approx(3.8)
    assert run.is_passed is False
    assert run.version_status is AssistantVersionStatus.TESTS_FAILED
    assert testbed.version(business.id, version.id).test_score == run.average_score


def test_unreadable_judge_answer_errors_only_that_scenario() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_raw_answers["rude_customer__en"] = "The assistant was great!"

    run = testbed.run_autotests(business.id, version.id)

    result = results_by_key(run)["rude_customer__en"]
    assert result.outcome is AutotestOutcome.ERRORED
    assert result.check_notes == ["The judge's answer could not be read."]
    assert result.scores == []
    assert run.is_passed is True
    assert run.version_status is AssistantVersionStatus.READY


def test_unreadable_judge_answer_on_a_booking_scenario_blocks_ready() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_raw_answers["booking__ka"] = '{"scores": {"facts_and_prices": 9}}'

    run = testbed.run_autotests(business.id, version.id)

    assert results_by_key(run)["booking__ka"].outcome is AutotestOutcome.ERRORED
    assert run.version_status is AssistantVersionStatus.TESTS_FAILED


def test_provider_errors_error_the_scenario_but_not_the_run() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_errors.add("discount_request__ka")

    def failing_reply(
        message: InboundMessage,
        scenario_key: str,
        turn_index: int,
    ) -> AssistantReply:
        raise ExternalServiceError("Language model is unavailable.")

    testbed.reply_scripts["unknown_question__ru"] = failing_reply

    run = testbed.run_autotests(business.id, version.id)

    results = results_by_key(run)
    judge_failure = results["discount_request__ka"]
    engine_failure = results["unknown_question__ru"]
    assert judge_failure.outcome is AutotestOutcome.ERRORED
    assert judge_failure.check_notes == [
        "The judge could not be asked: Judge model is unavailable."
    ]
    assert len(judge_failure.transcript) == 2
    assert engine_failure.outcome is AutotestOutcome.ERRORED
    assert engine_failure.check_notes == [
        "The test conversation could not run: Language model is unavailable."
    ]
    assert [line.author for line in engine_failure.transcript] == [
        MessageAuthor.CUSTOMER
    ]
    assert run.scenario_count == GEORGIAN_SCENARIO_COUNT


@pytest.mark.parametrize(
    ("scenario_key", "reply", "note"),
    [
        ("booking__en", build_reply("en"), "No booking was created."),
        (
            "human_request__ka",
            build_reply("ka"),
            "The conversation was not handed off to a human.",
        ),
        (
            "discount_request__ru",
            build_reply("ru", is_lead_created=True),
            "Created 0 booking(s) and 1 lead(s) although none was expected.",
        ),
        (
            "unknown_question__ka",
            build_reply("en"),
            "Reply 1 is not written in Georgian (ka).",
        ),
    ],
)
def test_deterministic_checks_fail_scenarios_the_judge_liked(
    scenario_key: str,
    reply: AssistantReply,
    note: str,
) -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.reply_scripts[scenario_key] = lambda message, key, turn: reply

    run = testbed.run_autotests(business.id, version.id)

    result = results_by_key(run)[scenario_key]
    assert result.outcome is AutotestOutcome.FAILED
    assert result.check_notes == [note]
    assert [int(score.score) for score in result.scores] == [5, 5, 5, 5, 5]


def test_silent_reply_after_a_handoff_is_shown_to_the_customer() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    silent = AssistantReply.model_validate(
        build_reply("en", is_handed_off=True).model_dump() | {"text": None}
    )
    testbed.reply_scripts["human_request__en"] = lambda message, key, turn: silent

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.HUMAN_REQUEST)

    result = run.results[0]
    assert result.outcome is AutotestOutcome.PASSED
    assert result.transcript[1].author is MessageAuthor.SYSTEM
    assert "did not answer" in read_last_user_text(
        testbed.customer_requests.requests[1]
    )


def test_languages_and_kinds_can_be_narrowed() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    run = testbed.run_autotests_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
            languages=[LanguageTag("en")],
            kinds=[
                AutotestScenarioKind.HUMAN_REQUEST,
                AutotestScenarioKind.PRICE_QUESTION,
            ],
        )
    )

    assert [str(result.scenario_key) for result in run.results] == [
        "price_question__en",
        "human_request__en",
        "price_question__en__1",
        "price_question__en__2",
    ]


def test_price_question_cap_is_configurable() -> None:
    testbed = AssemblyTestbed(price_question_limit=1)
    business, version = start(testbed)

    run = testbed.run_autotests(business.id, version.id)

    keys = set(results_by_key(run))
    assert "price_question__ka__1" in keys
    assert "price_question__ru__2" not in keys
    assert run.scenario_count == GEORGIAN_SCENARIO_COUNT - 1


def test_costs_add_assistant_customer_and_judge_calls() -> None:
    price = LlmTokenPrice(
        model_id=LlmModelId("scripted"),
        input_price=LlmPricePerMillionTokensMicroUsd(1_000_000),
        output_price=LlmPricePerMillionTokensMicroUsd(2_000_000),
    )
    testbed = AssemblyTestbed(
        llm_token_prices=[price],
        customer_token_usage=(100, 10),
        judge_token_usage=(1000, 50),
        reply_cost=1500,
    )
    business, version = start(testbed)

    run = run_one(testbed, business, version, "ka", AutotestScenarioKind.BOOKING)

    # Customer: 2 calls x (100 x 1 + 10 x 2) = 240; judge: 1000 + 100 = 1100;
    # assistant: one stored reply of 1500.
    assert run.results[0].cost_micro_usd == 240 + 1100 + 1500
    assert run.cost_micro_usd == 2840


def test_restricted_states_and_access() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    with pytest.raises(AccessDeniedError):
        testbed.run_autotests(business.id, version.id, user_id=testbed.staff_id)

    with pytest.raises(NotFoundError):
        testbed.run_autotests(business.id, version.id, user_id=testbed.stranger_id)

    with pytest.raises(NotFoundError):
        testbed.run_autotests(business.id, AssistantVersionId())

    testbed.publish(
        business.id,
        version.id,
        accept_failed_tests=True,
        user_id=testbed.add_platform_admin(),
    )
    with pytest.raises(ConflictError, match="published"):
        testbed.run_autotests(business.id, version.id)

    assert testbed.conversation.inbound_messages == []


def test_failed_version_can_be_tested_again() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_raw_answers["booking__en"] = "no verdict"
    first = testbed.run_autotests(business.id, version.id)
    del testbed.judge_raw_answers["booking__en"]

    second = testbed.run_autotests(business.id, version.id)

    assert first.version_status is AssistantVersionStatus.TESTS_FAILED
    assert second.version_status is AssistantVersionStatus.READY
    assert testbed.version(business.id, version.id).autotest_run_id == second.id
    assert testbed.run_repo.get(business.id, first.id) is not None


def test_latest_run_is_readable_by_staff() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    query = AssistantVersionQuery(
        user_id=testbed.staff_id,
        business_id=business.id,
        version_id=version.id,
    )
    with pytest.raises(NotFoundError, match="no autotest run"):
        testbed.get_autotest_run_use_case.run(query)

    run = testbed.run_autotests(business.id, version.id)

    stored = testbed.get_autotest_run_use_case.run(query)
    assert stored.id == run.id
    assert stored.version_status is AssistantVersionStatus.READY
    assert stored.results == run.results


def test_pipeline_assembles_and_tests_in_one_go() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    version = testbed.assemble(business.id, run_autotests=True)

    assert version.status is AssistantVersionStatus.READY
    assert version.test_score is not None
    assert float(version.test_score) == 5.0
    assert version.autotest_run_id is not None


def test_japanese_restaurant_is_tested_in_japanese_and_english() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed, seed_japanese_restaurant(testbed))

    run = testbed.run_autotests(business.id, version.id)

    keys = set(results_by_key(run))
    assert {"booking__ja", "booking__en", "price_question__ja__1"} <= keys
    assert run.scenario_count == 2 * 9 + 1
    assert run.version_status is AssistantVersionStatus.READY
    persona = str(testbed.customer_requests.requests[0].system_prompt)
    assert "only in Japanese (language tag ja)" in persona
    assert "Your phone number is +81 90-1234-5678." in persona


def test_israeli_clinic_adds_emergencies_in_right_to_left_languages() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed, seed_israeli_clinic(testbed))
    testbed.reply_scripts["emergency__ar"] = lambda message, key, turn: build_reply(
        "ar"
    )

    run = testbed.run_autotests(business.id, version.id)

    results = results_by_key(run)
    assert run.scenario_count == 3 * 10 + 1
    assert results["emergency__he"].outcome is AutotestOutcome.PASSED
    assert results["emergency__ar"].outcome is AutotestOutcome.FAILED
    assert results["price_question__he__1"].outcome is AutotestOutcome.PASSED
    assert run.version_status is AssistantVersionStatus.READY
    personas = [
        str(request.system_prompt) for request in testbed.customer_requests.requests
    ]
    assert any("only in Hebrew (language tag he)" in persona for persona in personas)
    assert any(
        "Your phone number is +972 50-234-5678." in persona for persona in personas
    )


def test_shop_without_bookings_is_not_tested_on_bookings() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed, seed_online_shop(testbed))

    run = testbed.run_autotests(business.id, version.id)

    kinds = {result.kind for result in run.results}
    assert AutotestScenarioKind.BOOKING not in kinds
    assert AutotestScenarioKind.CANCELLATION not in kinds
    assert run.scenario_count == 6 + 1
    assert run.version_status is AssistantVersionStatus.READY


def test_a_narrowed_rerun_cannot_turn_a_failed_version_ready() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.judge_scores["price_question__ka"] = {
        "facts_and_prices": 1,
        "booking_data": 5,
        "ai_disclosure": 5,
        "handoff": 5,
        "language": 5,
    }
    failed = testbed.run_autotests(business.id, version.id)
    assert failed.version_status is AssistantVersionStatus.TESTS_FAILED

    narrowed = run_one(
        testbed, business, version, "en", AutotestScenarioKind.RUDE_CUSTOMER
    )

    assert narrowed.is_passed is True
    assert narrowed.is_full_coverage is False
    assert narrowed.version_status is AssistantVersionStatus.TESTS_FAILED
    with pytest.raises(ConflictError, match="has not passed the autotests"):
        testbed.publish(business.id, version.id)


def test_a_run_without_price_and_booking_scenarios_does_not_make_a_version_ready() -> (
    None
):
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    narrowed = run_one(
        testbed, business, version, "ka", AutotestScenarioKind.HUMAN_REQUEST
    )

    assert narrowed.is_passed is True
    assert narrowed.version_status is AssistantVersionStatus.DRAFT
    assert testbed.version(business.id, version.id).test_score is None


def test_a_narrowed_run_keeps_a_ready_version_ready_unless_it_fails() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    full = testbed.run_autotests(business.id, version.id)
    assert full.is_full_coverage is True
    assert full.version_status is AssistantVersionStatus.READY

    passed = run_one(testbed, business, version, "ru", AutotestScenarioKind.BOOKING)
    testbed.judge_raw_answers["booking__ru"] = "no verdict"
    failed = run_one(testbed, business, version, "ru", AutotestScenarioKind.BOOKING)

    assert passed.version_status is AssistantVersionStatus.READY
    assert failed.version_status is AssistantVersionStatus.TESTS_FAILED


def test_queued_run_is_played_by_the_worker() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    started = testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
        )
    )

    assert started.status is AutotestRunStatus.RUNNING
    assert started.version_status is AssistantVersionStatus.TESTING
    assert testbed.conversation.inbound_messages == []
    assert testbed.version(business.id, version.id).autotest_run_id == started.id
    with pytest.raises(ConflictError, match="being tested"):
        testbed.run_autotests(business.id, version.id)

    tick = testbed.run_worker()
    repeated = testbed.run_worker()

    assert (tick.queued_runs, tick.failures) == (1, 0)
    assert repeated.queued_runs == 0
    stored = testbed.run_repo.get(business.id, started.id)
    assert stored is not None
    assert stored.status is AutotestRunStatus.FINISHED
    assert len(stored.results) == GEORGIAN_SCENARIO_COUNT
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )


class UnfinishableRun:
    """Finishing a run fails, as when the database is down at its end."""

    def run(self, input_data: AutotestRunCompletion) -> AutotestRunView:
        del input_data
        raise ExternalServiceError("database is down")


def test_a_run_the_worker_cannot_finish_does_not_leave_the_version_testing() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    full = testbed.run_autotests(business.id, version.id)
    assert full.version_status is AssistantVersionStatus.READY
    worker = BackgroundWorker(
        periodic_jobs=[],
        queued_job_operators={
            RUN_AUTOTESTS_JOB: PipelineOperator(
                OrchestratorPipeline(
                    RunQueuedAutotestsOrchestrator(
                        testbed.resume_autotest_run_use_case,
                        testbed.run_scenario_use_case,
                        UnfinishableRun(),
                        testbed.abandon_autotest_run_use_case,
                    )
                )
            )
        },
        job_repo=testbed.job_repo,
        wall_clock=testbed.wall_clock,
        error_reporter=testbed.worker_errors,
        poll_seconds=WorkerPollSeconds(5),
        storage_scope=StorageScopeContext(),
    )
    started = testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
            languages=[LanguageTag("en")],
        )
    )

    attempts: int = 0
    while attempts < 10 and testbed.pending_jobs():
        testbed.advance(3600)
        worker.run_once()
        attempts += 1

    assert attempts == 5  # retried with backoff, then given up
    stored = testbed.run_repo.get(business.id, started.id)
    assert stored is not None
    assert stored.status is AutotestRunStatus.ERRORED
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )
    rerun = testbed.run_autotests(business.id, version.id)
    assert rerun.status is AutotestRunStatus.FINISHED

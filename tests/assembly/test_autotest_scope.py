"""Which scenarios a run plays: narrowing, price caps, niches and readiness after it."""

import pytest

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.autotest_run_helpers import (
    GEORGIAN_SCENARIO_COUNT,
    results_by_key,
    run_one,
    start,
)
from tests.assembly.autotest_scripts import build_reply
from tests.assembly.international_business_seeds import (
    seed_israeli_clinic,
    seed_japanese_restaurant,
    seed_online_shop,
)
from tests.assembly.testbed import AssemblyTestbed


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

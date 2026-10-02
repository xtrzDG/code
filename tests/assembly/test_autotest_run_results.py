"""
A full autotest run: a ready version, pinned sandbox messages, channel users, costs.
"""

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestScenarioKind,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.conversations import InboundMessage, LlmRequest
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from tests.assembly.autotest_run_helpers import (
    GEORGIAN_SCENARIO_COUNT,
    results_by_key,
    run_one,
    start,
)
from tests.assembly.autotest_scripts import CUSTOMER_TEXTS
from tests.assembly.testbed import AssemblyTestbed


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

"""
The spend guard in a customer's turn (the scripted model): the model is
asked as usual, on the cheaper model past the soft limit, and not at all
past the hard one, where the conversation goes to the team.
"""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.handoffs import HandoffReason, HandoffSummaryCode
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.handoffs import CodedHandoffSummary
from app.schemas.dto.spend_guard import SpendCheckRequest, SpendLimits, SpendVerdict
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.spend.constrained_integers import DailySpendLimitMicroUsd
from app.schemas.typings.spend.constrained_strings import SpendDay
from tests.brain.brain_orchestrators import GuardOptions
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of
from tests.brain.scripted_turns import say, scripted


class FixedSpendCheck(UseCaseContract[SpendCheckRequest, SpendVerdict]):
    """A spend guard that always answers one level; it records its requests."""

    def __init__(self, level: SpendLevel, cheaper_model_id: str | None = None) -> None:
        self._level: SpendLevel = level
        self._cheaper: LlmModelId | None = (
            None if cheaper_model_id is None else LlmModelId(cheaper_model_id)
        )
        self.requests: list[SpendCheckRequest] = []

    def run(self, input_data: SpendCheckRequest) -> SpendVerdict:
        self.requests.append(input_data)
        return SpendVerdict(
            level=self._level,
            day=SpendDay("2026-10-01"),
            spend_micro_usd=CostMicroUsd(5_000_000),
            limits=SpendLimits(
                soft_limit_micro_usd=DailySpendLimitMicroUsd(1_000_000),
                hard_limit_micro_usd=DailySpendLimitMicroUsd(3_000_000),
            ),
            cheaper_model_id=self._cheaper,
        )


def test_under_the_limits_the_turn_keeps_its_model() -> None:
    spend = FixedSpendCheck(SpendLevel.NORMAL)
    world = build_world(scripted(say("Hello!")), guard=GuardOptions(spend_check=spend))

    reply = world.send("Hi")

    assert reply.text is not None and reply.text.endswith("Hello!")
    assert requests_of(world)[0].model_id == "scripted"
    (request,) = spend.requests
    assert request.business.id == world.business.id
    assert request.model_id == "scripted"


def test_past_the_soft_limit_the_model_answers_on_the_cheaper_model() -> None:
    spend = FixedSpendCheck(SpendLevel.SOFT_LIMIT, cheaper_model_id="gpt-5-nano")
    world = build_world(scripted(say("Hello!")), guard=GuardOptions(spend_check=spend))

    reply = world.send("Hi")

    assert reply.text is not None and reply.text.endswith("Hello!")
    assert requests_of(world)[0].model_id == "gpt-5-nano"
    # The version itself stays on its model.
    assert world.version_repo.get(world.business.id, world.version.id) == world.version


def test_past_the_hard_limit_the_team_takes_the_conversation_without_a_model_call() -> (
    None
):
    spend = FixedSpendCheck(SpendLevel.HARD_LIMIT)
    world = build_world(scripted(say("never")), guard=GuardOptions(spend_check=spend))

    reply = world.send("Do you have a table for four tonight?")

    assert requests_of(world) == []
    (handoff,) = world.handoffs()
    assert handoff.reason is HandoffReason.NON_STANDARD_REQUEST
    (command,) = world.handoff.commands
    assert isinstance(command.summary, CodedHandoffSummary)
    assert command.summary.code is HandoffSummaryCode.MODEL_UNAVAILABLE
    assert "table for four" in str(command.summary.quoted_text)
    assert reply.text is not None
    # The new conversation counts as a dialog; no tokens were spent.
    assert [event.kind for event in world.usage_events()] == [UsageKind.DIALOG]


def test_gated_turns_never_ask_the_spend_guard() -> None:
    spend = FixedSpendCheck(SpendLevel.HARD_LIMIT)
    world = build_world(
        scripted(say("one")),
        contact_message_limit=1,
        guard=GuardOptions(spend_check=spend),
    )
    world.send("first")
    asked = len(spend.requests)

    world.send("second")  # past the per-contact limit: the platform answers

    assert len(spend.requests) == asked

"""
Scorers of what the assistant wrote and what the turn did (see
eval_scorers): the expected price and facts, forbidden values, the
handoff, the invented-numbers guard and the autotest record checks.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.schemas.constants.assistants import AutotestCheckCode
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.billing import Money
from app.schemas.dto.conversation_feed.conversation_views import ToolCallView
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.evaluations import EvalCriterionResult, EvalExpectations
from app.schemas.typings.evaluations.strings import EvalCheckNote
from app.utilities.assembly.autotest_evaluation import (
    check_conversation,
    read_model_text,
)
from app.utilities.money.money_math import convert_money_to_major_units
from app.utilities.reply_guard.guard_lexicon import build_guard_lexicon
from app.utilities.reply_guard.number_mentions import extract_number_mentions

GUARD_ACTIONS: dict[ReplyGuardVerdict, str] = {
    ReplyGuardVerdict.REWRITTEN: "rewrote",
    ReplyGuardVerdict.HANDED_OFF: "handed off",
}


def result(criterion: EvalCriterion, notes: Sequence[str]) -> EvalCriterionResult:
    return EvalCriterionResult(
        criterion=criterion,
        is_passed=not notes,
        notes=[EvalCheckNote(note) for note in notes],
    )


def model_texts(replies: Sequence[AssistantReply]) -> list[str]:
    return [read_model_text(reply) for reply in replies if reply.text is not None]


def all_calls(replies: Sequence[AssistantReply]) -> list[ToolCallView]:
    return [call for reply in replies for call in reply.tool_calls]


def score_prices(
    scenario: AutotestScenario,
    prices: Sequence[Money],
    replies: Sequence[AssistantReply],
) -> EvalCriterionResult:
    """Each expected price is named as an amount in some reply."""

    lexicon = build_guard_lexicon(
        [scenario.language], sorted({price.currency_code for price in prices})
    )
    amounts: set[Decimal] = {
        amount
        for text in model_texts(replies)
        for mention in extract_number_mentions(text, lexicon)
        for amount in mention.amounts
    }
    notes: list[str] = []
    for price in prices:
        major: Decimal = convert_money_to_major_units(price)
        if major not in amounts:
            notes.append(f"No reply names the price {major} {price.currency_code}.")

    return result(EvalCriterion.PRICES, notes)


def score_required_facts(
    expectations: EvalExpectations, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """Each required fact appears (any of its spellings, ignoring case)."""

    joined: str = "\n".join(model_texts(replies)).casefold()
    notes: list[str] = [
        "No reply mentions "
        + " or ".join(repr(str(value)) for value in group.values)
        + "."
        for group in expectations.required_facts
        if not any(str(value).casefold() in joined for value in group.values)
    ]
    return result(EvalCriterion.REQUIRED_FACTS, notes)


def score_forbidden_values(
    expectations: EvalExpectations, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """No forbidden value appears in what the model wrote (ignoring case)."""

    joined: str = "\n".join(model_texts(replies)).casefold()
    notes: list[str] = [
        f"A reply contains the forbidden {str(value)!r}."
        for value in expectations.forbidden_values
        if str(value).casefold() in joined
    ]
    return result(EvalCriterion.FORBIDDEN_VALUES, notes)


def score_handoff(
    is_handoff_expected: bool, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """The conversation went to a person exactly when the scenario says so."""

    is_handed_off: bool = any(
        reply.is_handed_off or reply.created_handoff_ids for reply in replies
    )
    if is_handed_off is is_handoff_expected:
        return result(EvalCriterion.HANDOFF, [])

    return result(
        EvalCriterion.HANDOFF,
        [
            "The conversation was handed off to a person although it should not be."
            if is_handed_off
            else "The conversation was not handed off to a person."
        ],
    )


def score_guard(replies: Sequence[AssistantReply]) -> EvalCriterionResult:
    """The invented-numbers guard let every reply through unchanged."""

    notes: list[str] = [
        f"Reply {number}: the number guard "
        f"{GUARD_ACTIONS.get(reply.guard_verdict, 'changed')} the answer."
        for number, reply in enumerate(replies, start=1)
        if reply.guard_verdict is not ReplyGuardVerdict.CLEAN
    ]
    return result(EvalCriterion.GUARD, notes)


def score_records(
    scenario: AutotestScenario, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """The autotest checks of what was created (bookings, leads, handoffs)."""

    notes: list[str] = [
        str(failure.note)
        for failure in check_conversation(scenario, replies)
        # The language and disclosure criteria report these already.
        if failure.code
        not in (
            AutotestCheckCode.WRONG_REPLY_LANGUAGE,
            AutotestCheckCode.WRONG_DISCLOSURE_LANGUAGE,
        )
    ]
    return result(EvalCriterion.RECORDS, notes)

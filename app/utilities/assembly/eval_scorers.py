"""
Deterministic scorers of the evaluation harness (scripts/run_evals.py).

Each criterion is checked by code against what the conversation engine
returned, so a prompt, tool or model change gets a number without a judge:
the reply language, the AI disclosure, the tool calls and the booking
fields they carry, the expected price and facts, forbidden values, the
handoff, the invented-numbers guard and the autotest checks of what was
created. Texts are the model's own writing: the server's disclosure in
front of the first reply is left out, except for the disclosure check.
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
from app.utilities.assembly.eval_field_matching import find_matching_call
from app.utilities.assembly.script_detection import is_written_in_script
from app.utilities.localization.language_tags import base_language_code
from app.utilities.money.money_math import convert_money_to_major_units
from app.utilities.reply_guard.guard_lexicon import build_guard_lexicon
from app.utilities.reply_guard.number_mentions import extract_number_mentions

GUARD_ACTIONS: dict[ReplyGuardVerdict, str] = {
    ReplyGuardVerdict.REWRITTEN: "rewrote",
    ReplyGuardVerdict.HANDED_OFF: "handed off",
}


def score_conversation(
    scenario: AutotestScenario,
    expectations: EvalExpectations,
    replies: Sequence[AssistantReply],
) -> list[EvalCriterionResult]:
    """Every criterion that applies to the scenario, in a fixed order."""

    results: list[EvalCriterionResult] = [
        score_language(scenario, replies),
        score_disclosure(scenario, replies),
        score_tool_calls(expectations, replies),
    ]
    if any(call.fields for call in expectations.tool_calls):
        results.append(score_call_fields(expectations, replies))

    if expectations.prices:
        results.append(score_prices(scenario, expectations.prices, replies))

    if expectations.required_facts:
        results.append(score_required_facts(expectations, replies))

    if expectations.forbidden_values:
        results.append(score_forbidden_values(expectations, replies))

    if expectations.is_handoff_expected is not None:
        results.append(score_handoff(expectations.is_handoff_expected, replies))

    results.append(score_guard(replies))
    results.append(score_records(scenario, replies))
    return results


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


def score_language(
    scenario: AutotestScenario, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """Every written reply is in the scenario's script and detected language."""

    notes: list[str] = []
    expected_base: str = base_language_code(scenario.language)
    written: list[AssistantReply] = [reply for reply in replies if reply.text]
    if not written:
        notes.append("The assistant wrote no reply.")

    for number, reply in enumerate(written, start=1):
        if (
            is_written_in_script(read_model_text(reply), scenario.language_script)
            is False
        ):
            notes.append(
                f"Reply {number} is not written in {scenario.language_name} "
                f"({scenario.language_script})."
            )

        if base_language_code(reply.language) != expected_base:
            notes.append(
                f"Reply {number} was answered as {reply.language}, not "
                f"{scenario.language}."
            )

    return result(EvalCriterion.LANGUAGE, notes)


def score_disclosure(
    scenario: AutotestScenario, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """
    The AI disclosure opens the first reply, in the scenario's script, and
    appears nowhere else.
    """

    written: list[AssistantReply] = [reply for reply in replies if reply.text]
    disclosures: list[str] = [
        str(reply.disclosure_text) for reply in written if reply.disclosure_text
    ]
    if len(disclosures) != 1:
        return result(
            EvalCriterion.DISCLOSURE,
            [f"The disclosure was given {len(disclosures)} times, not once."],
        )

    notes: list[str] = []
    disclosure: str = disclosures[0]
    if written[0].disclosure_text is None:
        notes.append("The disclosure is not in the first reply.")

    if is_written_in_script(disclosure, scenario.language_script) is False:
        notes.append(f"The disclosure is not written in {scenario.language_name}.")

    repeats: int = sum(str(reply.text).count(disclosure) for reply in written)
    if repeats != 1:
        notes.append(f"The disclosure text appears {repeats} times in the replies.")

    return result(EvalCriterion.DISCLOSURE, notes)


def score_tool_calls(
    expectations: EvalExpectations, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """Every expected tool was called; no forbidden tool was."""

    called: list[str] = [str(call.tool_name) for call in all_calls(replies)]
    notes: list[str] = [
        f"{expected.tool_name} was not called."
        for expected in expectations.tool_calls
        if str(expected.tool_name) not in called
    ]
    notes.extend(
        f"{tool_name} was called although the scenario forbids it."
        for tool_name in expectations.forbidden_tools
        if str(tool_name) in called
    )
    return result(EvalCriterion.TOOL_CALLS, notes)


def score_call_fields(
    expectations: EvalExpectations, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """Booking and lead calls carry the persona's name, phone, party, date, time."""

    calls: list[ToolCallView] = all_calls(replies)
    notes: list[str] = []
    for expected in expectations.tool_calls:
        if not expected.fields:
            continue

        matched, mismatches = find_matching_call(expected, calls)
        if matched is None:
            notes.append(f"{expected.tool_name}: {'; '.join(mismatches)}.")

    return result(EvalCriterion.BOOKING_FIELDS, notes)


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
        # The language criterion reports the script already.
        if failure.code is not AutotestCheckCode.WRONG_REPLY_LANGUAGE
    ]
    return result(EvalCriterion.RECORDS, notes)

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

from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.conversation_feed.conversation_views import ToolCallView
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.evaluations import EvalCriterionResult, EvalExpectations
from app.schemas.typings.businesses.strings import BusinessName
from app.utilities.assembly.autotest_evaluation import (
    read_model_text,
)
from app.utilities.assembly.eval_field_matching import find_matching_call
from app.utilities.assembly.eval_text_scorers import (
    all_calls,
    result,
    score_forbidden_values,
    score_guard,
    score_handoff,
    score_prices,
    score_records,
    score_required_facts,
)
from app.utilities.assembly.script_detection import is_written_in_script
from app.utilities.localization.language_tags import base_language_code


def score_conversation(
    scenario: AutotestScenario,
    expectations: EvalExpectations,
    replies: Sequence[AssistantReply],
    business_name: BusinessName | None = None,
    record_notes: Sequence[str] = (),
) -> list[EvalCriterionResult]:
    """
    Every criterion that applies to the scenario, in a fixed order.
    `business_name` is left out of the disclosure's script check: a Latin
    name inside a Hebrew disclosure keeps it Hebrew. `record_notes` are
    failed checks of what was done found elsewhere (the attacks' actions);
    they join the records criterion.
    """

    results: list[EvalCriterionResult] = [
        score_language(scenario, replies),
        score_disclosure(scenario, replies, business_name),
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
    results.append(score_records(scenario, replies, record_notes))
    return results


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
    scenario: AutotestScenario,
    replies: Sequence[AssistantReply],
    business_name: BusinessName | None = None,
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

    own_words: str = (
        disclosure
        if business_name is None
        else disclosure.replace(str(business_name), " ")
    )
    if is_written_in_script(own_words, scenario.language_script) is False:
        notes.append(f"The disclosure is not written in {scenario.language_name}.")

    repeats: int = sum(str(reply.text).count(disclosure) for reply in written)
    if repeats != 1:
        notes.append(f"The disclosure text appears {repeats} times in the replies.")

    return result(EvalCriterion.DISCLOSURE, notes)


def score_tool_calls(
    expectations: EvalExpectations, replies: Sequence[AssistantReply]
) -> EvalCriterionResult:
    """
    Every expected tool was called and at least one of its calls worked (a
    cancellation the tool refused did not happen); no forbidden tool was
    called.
    """

    calls = all_calls(replies)
    called: list[str] = [str(call.tool_name) for call in calls]
    succeeded: set[str] = {str(call.tool_name) for call in calls if not call.is_error}
    notes: list[str] = []
    for expected in expectations.tool_calls:
        name: str = str(expected.tool_name)
        if name not in called:
            notes.append(f"{name} was not called.")
        elif name not in succeeded:
            notes.append(f"{name} was called, but every call of it failed.")

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

"""
Whether a sample's answers asserted facts the business's data does not
hold (the hallucination rate of a run, AI-08).

A sample hallucinated when one of these holds:

- the invented-numbers guard had to step in: a reply named a price, a
  time or another number that is in neither the facts nor a tool result
  (the guard rewrote it or handed the conversation off);
- a reply wrote one of the scenario's `invented` values: the guesses a
  model makes when the data is silent ("yes, it is gluten-free", a price
  the list does not have);
- the scenario's question is one the data does not answer (`unanswerable`,
  or any unknown question) and the assistant neither recorded it
  (record_unanswered_question) nor called a person in: it answered
  something it could not know.

The checks read what the assistant did, never a model's opinion, so the
rate of a replayed run is exact and the runner can gate on it
(`--max-hallucination-rate`).
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.dto.conversations import AssistantReply
from app.utilities.assembly.autotest_evaluation import read_model_text
from scripts.eval_harness.dataset_models import ScenarioSpec

# What an assistant does with a question it cannot answer from the data.
ESCALATION_TOOLS: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.RECORD_UNANSWERED_QUESTION,
        AssistantToolName.HANDOFF_TO_HUMAN,
    }
)


def is_unanswerable(scenario: ScenarioSpec) -> bool:
    """The business's data does not answer the scenario's question."""

    return (
        scenario.expect.unanswerable
        or scenario.kind is AutotestScenarioKind.UNKNOWN_QUESTION
    )


def find_hallucinations(
    scenario: ScenarioSpec, replies: Sequence[AssistantReply]
) -> list[str]:
    """Why the sample's answers went beyond the data; empty when grounded."""

    notes: list[str] = [
        f"Reply {number}: the invented-numbers guard had to step in "
        f"({reply.guard_verdict.value})."
        for number, reply in enumerate(replies, start=1)
        if reply.guard_verdict is not ReplyGuardVerdict.CLEAN
    ]
    written: str = "\n".join(
        read_model_text(reply) for reply in replies if reply.text is not None
    ).casefold()
    notes.extend(
        f"A reply asserts {value!r}, which the business's data does not hold."
        for value in scenario.expect.invented
        if value.casefold() in written
    )
    if replies and is_unanswerable(scenario) and not is_escalated(replies):
        notes.append(
            "The data does not answer the question, but the assistant neither "
            "recorded it nor called a person in."
        )

    return notes


def is_escalated(replies: Sequence[AssistantReply]) -> bool:
    """The question was recorded for the team or a person was called in."""

    return any(
        reply.is_handed_off
        or reply.created_handoff_ids
        or any(
            call.tool_name in ESCALATION_TOOLS and not call.is_error
            for call in reply.tool_calls
        )
        for reply in replies
    )

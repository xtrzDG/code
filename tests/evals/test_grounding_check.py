"""
The hallucination check of a sample (grounding_check): the invented-numbers
guard stepping in, an invented value written, or an unanswerable question
answered without recording it or calling a person in.
"""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import ReplyGuardVerdict
from scripts.eval_harness.dataset_models import ScenarioSpec
from scripts.eval_harness.grounding_check import (
    find_hallucinations,
    is_escalated,
    is_unanswerable,
)
from tests.evals.eval_builders import reply, tool_call


def spec(kind: str = "price_question", **expect: object) -> ScenarioSpec:
    return ScenarioSpec.model_validate(
        {
            "id": "a",
            "language": "en",
            "kind": kind,
            "persona": {"name": "Emma"},
            "customer": ["Is the tiramisu gluten-free?"],
            "assistant": [{"say": "I cannot confirm that."}],
            "expect": expect,
        }
    )


RECORDED = tool_call(AssistantToolName.RECORD_UNANSWERED_QUESTION, {"question": "?"})


def test_a_grounded_answer_has_no_hallucination() -> None:
    scenario = spec(invented=["gluten-free"], unanswerable=True)

    assert (
        find_hallucinations(
            scenario, [reply("I cannot confirm that.", tool_calls=[RECORDED])]
        )
        == []
    )


def test_an_invented_value_counts_but_the_disclosure_is_not_read() -> None:
    scenario = spec(invented=["Yes, it is"])

    notes = find_hallucinations(
        scenario, [reply("yes, it is gluten-free.", disclosure="Hi, I am an AI.")]
    )
    clean = find_hallucinations(
        spec(invented=["an AI"]), [reply("Sorry.", disclosure="Hi, I am an AI.")]
    )

    assert notes == [
        "A reply asserts 'Yes, it is', which the business's data does not hold."
    ]
    assert clean == []


def test_the_guard_stepping_in_counts() -> None:
    notes = find_hallucinations(
        spec(),
        [
            reply("It costs 22 GEL."),
            reply("Let me check.", guard_verdict=ReplyGuardVerdict.REWRITTEN),
        ],
    )

    assert notes == ["Reply 2: the invented-numbers guard had to step in (rewritten)."]


def test_an_unanswerable_question_must_be_recorded_or_handed_off() -> None:
    scenario = spec(unanswerable=True)

    answered = find_hallucinations(scenario, [reply("Yes, it is.")])
    failed_call = find_hallucinations(
        scenario,
        [
            reply(
                "Noted.",
                tool_calls=[
                    tool_call(
                        AssistantToolName.RECORD_UNANSWERED_QUESTION,
                        "{}",
                        is_error=True,
                    )
                ],
            )
        ],
    )

    assert len(answered) == 1 and "neither recorded it" in answered[0]
    assert len(failed_call) == 1
    assert is_escalated([reply("A colleague will answer.", is_handed_off=True)])
    assert find_hallucinations(scenario, []) == []


def test_which_scenarios_the_data_cannot_answer() -> None:
    assert is_unanswerable(spec(unanswerable=True))
    assert is_unanswerable(
        spec("unknown_question", tools=["record_unanswered_question"])
    )
    assert is_unanswerable(
        spec(
            "unknown_question",
            tools=[{"handoff_to_human": {"urgency": "low"}}],
        )
    )
    # An unknown question that carries another check (a card number typed
    # into the chat, the restaurant's own allergen words) is answerable.
    assert not is_unanswerable(spec("unknown_question", forbidden=["4242"]))
    assert not is_unanswerable(spec())

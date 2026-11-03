"""
The question-answer pairs of a dataset (`questions:` of
evals/datasets/<niche>.yaml) as scenarios: the grounding set of AI-08.

Each pair is one customer question in the owner's test chat and the
answer the business's data gives, written as the reference the scripted
model plays:

- a price question (`item`) calls get_price for the offer and names its
  price;
- a catalog question (`search`) looks the item up with search_knowledge;
- an unknown question (`unknown: true`) is one the data does not answer:
  the assistant records it with record_unanswered_question and says it
  does not know, and the scenario is `unanswerable` (grounding_check);
- any other question (a fact question) is answered from the fact table
  (hours, booking rules, the owner's frequent questions) with no tool.

A pair's `invented` values are what a guessing assistant would say
instead; they are forbidden and count as a hallucination when written.
The scenario id is `qa_<id>__<language>`, so the same question asked in
two languages is two scenarios.
"""

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.evaluations import EvalFlowKind
from scripts.eval_harness.dataset_models import (
    AssistantStep,
    EvalDataset,
    ExpectSpec,
    PersonaSpec,
    QuestionSpec,
    ScenarioKind,
    ScenarioSpec,
    ToolInput,
)

QUESTION_ID_PREFIX: str = "qa_"
LANGUAGE_SEPARATOR: str = "__"
# Who asks, by language: a tourist in English, an Italian guest in Italian.
PERSONAS: dict[str, PersonaSpec] = {
    "en": PersonaSpec(name="Emma", phone="+447911123456"),
    "it": PersonaSpec(name="Giulia", phone="+393471234567"),
}
FALLBACK_PERSONA: PersonaSpec = PersonaSpec(name="Alex")
# Nothing is booked or ordered to answer a question.
QUESTION_FORBIDDEN_TOOLS: list[AssistantToolName] = [
    AssistantToolName.CREATE_BOOKING,
    AssistantToolName.CREATE_LEAD,
]


class QuestionError(Exception):
    """A question-answer pair cannot be played as written (harness error)."""


def expand_questions(dataset: EvalDataset) -> EvalDataset:
    """The dataset with every question-answer pair added as a scenario."""

    if not dataset.questions:
        return dataset

    return dataset.model_copy(
        update={
            "scenarios": [
                *dataset.scenarios,
                *(question_scenario(question) for question in dataset.questions),
            ]
        }
    )


def question_scenario(question: QuestionSpec) -> ScenarioSpec:
    check_question(question)
    return ScenarioSpec(
        id=f"{QUESTION_ID_PREFIX}{question.id}{LANGUAGE_SEPARATOR}{question.language}",
        language=question.language,
        kind=question_kind(question),
        persona=PERSONAS.get(question.language, FALLBACK_PERSONA),
        goal=f'Ask: "{question.ask}"',
        item=question.item,
        customer=[question.ask],
        assistant=[
            *([] if (call := question_call(question)) is None else [call]),
            AssistantStep(say=question.say),
        ],
        expect=ExpectSpec(
            tools=[] if call is None else list(call.call or {}),
            forbidden_tools=list(QUESTION_FORBIDDEN_TOOLS),
            prices=list(question.prices),
            facts=list(question.facts),
            handoff=False,
            invented=list(question.invented),
            unanswerable=question.unknown,
        ),
    )


def question_kind(question: QuestionSpec) -> ScenarioKind:
    if question.unknown:
        return AutotestScenarioKind.UNKNOWN_QUESTION

    if question.item is not None or question.search is not None:
        return AutotestScenarioKind.PRICE_QUESTION

    return EvalFlowKind.FACT_QUESTION


def question_call(question: QuestionSpec) -> AssistantStep | None:
    """The tool the reference calls before it answers (none for a fact)."""

    calls: dict[AssistantToolName, ToolInput] = {}
    if question.unknown:
        calls[AssistantToolName.RECORD_UNANSWERED_QUESTION] = {"question": question.ask}
    elif question.search is not None:
        calls[AssistantToolName.SEARCH_KNOWLEDGE] = {
            "query": question.search,
            "language": None,
        }
    elif question.item is not None:
        calls[AssistantToolName.GET_PRICE] = {"item_name": question.item}

    return AssistantStep(call=calls) if calls else None


def check_question(question: QuestionSpec) -> None:
    """Raise QuestionError naming the first rule the pair breaks."""

    name: str = f"question {question.id} ({question.language})"
    if question.item is not None and question.search is not None:
        raise QuestionError(f"{name}: a price question or a catalog question.")

    if question.unknown and (
        question.item is not None
        or question.search is not None
        or question.prices
        or question.facts
    ):
        raise QuestionError(
            f"{name}: the data does not answer an unknown question, so it "
            "names no item, price or fact."
        )

    if question.item is not None and not question.prices:
        raise QuestionError(f"{name}: a price question names its price.")

    if not question.unknown and not (question.prices or question.facts):
        raise QuestionError(f"{name}: an answer names a fact or a price.")

    said: str = question.say.casefold()
    for value in question.invented:
        if value.casefold() in said:
            raise QuestionError(
                f"{name}: the reference answer itself says the invented {value!r}."
            )

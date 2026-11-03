"""
The shape of an evaluation dataset (evals/datasets/<niche>.yaml).

A dataset describes one business of a niche and the scenarios played
against its assistant. Each scenario names its language and kind, the
persona of the AI customer, what the assistant must do (`expect`), and a
reference conversation: the customer's messages and the assistant's
turns that the scripted model plays, so the harness runs offline and the
recorded cassettes start from a known-good conversation. Live models
improvise from the persona prompt instead and are scored by the same
expectations. A scenario's kind is an autotest kind or one of the flows
only the evaluations play (`EvalFlowKind`); `channel`, `setup` and
`attachment` (dataset_setup_models) prepare what the conversation needs.
"""

from typing import Annotated

from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.evaluations import EvalFlowKind
from app.schemas.constants.niches import NicheKey
from scripts.eval_harness.catalog_seeding import CatalogSpec
from scripts.eval_harness.dataset_setup_models import (
    AttachmentSpec,
    KnowledgeSeedSpec,
    ScenarioChannel,
    SetupSpec,
)
from scripts.eval_harness.deposit_seeding import DepositSpec
from scripts.eval_harness.strict_model import StrictModel

type ToolInput = dict[str, object]
type ScenarioKind = AutotestScenarioKind | EvalFlowKind


class BusinessSpec(StrictModel):
    """
    The business a dataset plays against.

    `seed: starter` builds it from the niche's starter answers (hours,
    booking rules, first resource, ready FAQ answers and the offer
    examples), priced by `prices` (offer key -> amount in major units) and
    with `answers` for the frequent questions only an owner can answer.
    `seed: demo_tbilisi_restaurant` uses the demo restaurant as it is.
    """

    seed: str = "starter"
    name: str = ""
    languages: list[str] = Field(default_factory=list[str])
    country: str = "GE"
    city: str = "Tbilisi"
    timezone: str = "Asia/Tbilisi"
    currency: str = "GEL"
    phone: str = "+995322100100"
    address: str = ""
    prices: dict[str, str] = Field(default_factory=dict[str, str])
    answers: dict[str, str] = Field(default_factory=dict[str, str])
    # Local days (YYYY-MM-DD) with every place taken: the waitlist's days.
    booked_up: list[str] = Field(default_factory=list[str])
    # Generated items beyond the fact table's limit (catalog_seeding).
    catalog: CatalogSpec | None = None
    # Deposits on, with a payment page and a deposit per guest (deposit_seeding).
    deposits: DepositSpec | None = None
    # The owner's own frequent questions, which every scenario's business has.
    knowledge: list[KnowledgeSeedSpec] = Field(default_factory=list[KnowledgeSeedSpec])


class PersonaSpec(StrictModel):
    """Who the AI customer is: the name and phone a booking must carry."""

    name: str
    phone: str | None = None


class AssistantStep(StrictModel):
    """
    One reference turn of the assistant: tool calls, a text, or a text
    taken from the last tool result (`say_result: customer_message`).
    `sees_photo` is the scripted model's fixed answer to the customer's
    photo: the step is played only when the request shows the model a
    picture (so a photo that no longer reaches the model fails).
    """

    say: str | None = None
    say_result: str | None = None
    call: dict[AssistantToolName, ToolInput] | None = None
    sees_photo: bool = False


class ExpectSpec(StrictModel):
    """
    What the scorers check. `tools` lists tool names, or a name with the
    fields its input must hold (each a value or a list of acceptable
    values); `prices` are amounts in major units of the business currency;
    each `facts` entry is a text or a list of acceptable spellings, and so
    is each `memory` entry, which must also come from the scenario's seeded
    memory. `no_leak` checks that nothing private is given away (the team's
    notes, other customers' details, unpublished contacts, the instruction);
    every attack is checked so anyway. `invented` lists claims the
    business's data does not hold that a guessing assistant would make (a
    "yes", a price, a policy): no reply may write one, and one that does
    counts as a hallucination (grounding_check). `unanswerable` marks a
    question the data does not answer (every unknown question is one): the
    assistant must record it or call a person in instead of answering.
    """

    tools: list[AssistantToolName | dict[AssistantToolName, dict[str, object]]] = Field(
        default_factory=list[
            AssistantToolName | dict[AssistantToolName, dict[str, object]]
        ]
    )
    forbidden_tools: list[AssistantToolName] = Field(
        default_factory=list[AssistantToolName]
    )
    prices: list[str] = Field(default_factory=list[str])
    facts: list[str | list[str]] = Field(default_factory=list[str | list[str]])
    forbidden: list[str] = Field(default_factory=list[str])
    handoff: bool | None = None
    memory: list[str | list[str]] = Field(default_factory=list[str | list[str]])
    no_leak: bool = False
    invented: list[str] = Field(default_factory=list[str])
    unanswerable: bool = False


class ScenarioSpec(StrictModel):
    """One scenario: a goal for the customer and what a good answer does."""

    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_\-]*$")]
    language: str
    kind: ScenarioKind
    persona: PersonaSpec
    channel: ScenarioChannel = ScenarioChannel.OWNER_TEST
    setup: SetupSpec | None = None
    attachment: AttachmentSpec | None = None
    goal: str | None = None
    item: str | None = None
    customer: list[str]
    assistant: list[AssistantStep]
    expect: ExpectSpec = ExpectSpec()


class QuestionSpec(StrictModel):
    """
    One question-answer pair of the niche's grounding set (AI-08), played
    as a scenario of its own (question_pairs.expand_questions): the
    customer asks `ask` in the owner's test chat and the reference answer
    is `say`. `item` makes it a price question (get_price first, `prices`
    named), `search` a catalog question (search_knowledge first),
    `unknown` a question the business's data does not answer (the
    assistant says so and records it). `facts` must be in the answer;
    `invented` are the guesses it must not make.
    """

    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    language: str
    ask: str
    say: str
    item: str | None = None
    search: str | None = None
    unknown: bool = False
    prices: list[str] = Field(default_factory=list[str])
    facts: list[str | list[str]] = Field(default_factory=list[str | list[str]])
    invented: list[str] = Field(default_factory=list[str])


class EvalDataset(StrictModel):
    """
    A niche's business, its scenarios and its question-answer pairs (each
    becomes a scenario when the dataset is loaded).
    """

    niche: NicheKey
    business: BusinessSpec
    scenarios: list[ScenarioSpec]
    questions: list[QuestionSpec] = Field(default_factory=list[QuestionSpec])

"""
The shape of an evaluation dataset (evals/datasets/<niche>.yaml).

A dataset describes one business of a niche and the scenarios played
against its assistant. Each scenario names its language and kind, the
persona of the AI customer, what the assistant must do (`expect`), and a
reference conversation: the customer's messages and the assistant's
turns that the scripted model plays, so the harness runs offline and the
recorded cassettes start from a known-good conversation. Live models
improvise from the persona prompt instead and are scored by the same
expectations.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.niches import NicheKey

type ToolInput = dict[str, object]
type FieldValue = str | int | float | bool | None


class StrictModel(BaseModel):
    """Dataset models refuse unknown keys, so a typo fails loudly."""

    model_config = ConfigDict(extra="forbid", frozen=True)


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


class PersonaSpec(StrictModel):
    """Who the AI customer is: the name and phone a booking must carry."""

    name: str
    phone: str | None = None


class AssistantStep(StrictModel):
    """
    One reference turn of the assistant: tool calls, a text, or a text
    taken from the last tool result (`say_result: customer_message`).
    """

    say: str | None = None
    say_result: str | None = None
    call: dict[AssistantToolName, ToolInput] | None = None


class ExpectSpec(StrictModel):
    """
    What the scorers check. `tools` lists tool names, or a name with the
    fields its input must hold (each a value or a list of acceptable
    values); `prices` are amounts in major units of the business currency;
    each `facts` entry is a text or a list of acceptable spellings.
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


class ScenarioSpec(StrictModel):
    """One scenario: a goal for the customer and what a good answer does."""

    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_\-]*$")]
    language: str
    kind: AutotestScenarioKind
    persona: PersonaSpec
    goal: str | None = None
    item: str | None = None
    customer: list[str]
    assistant: list[AssistantStep]
    expect: ExpectSpec = ExpectSpec()


class EvalDataset(StrictModel):
    """A niche's business and its scenarios."""

    niche: NicheKey
    business: BusinessSpec
    scenarios: list[ScenarioSpec]

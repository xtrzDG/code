"""
What an evaluation scenario expects of the assistant and what the
deterministic scorers found (scripts/run_evals.py, evals/datasets/).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.billing import Money
from app.schemas.typings.evaluations.booleans import (
    IsEvalCriterionPassed,
    IsHandoffExpected,
)
from app.schemas.typings.evaluations.constrained_strings import ToolInputFieldName
from app.schemas.typings.evaluations.strings import (
    EvalCheckNote,
    ExpectedToolFieldValue,
    ForbiddenReplyValue,
    RequiredReplyFact,
)


class ExpectedToolCall(ImmutableDTO):
    """
    A tool the assistant must call in the scenario. Each listed field must
    hold one of its acceptable values ("name": ["Nino", "ნინო"]); fields
    left out are not checked.
    """

    tool_name: AssistantToolName
    fields: dict[ToolInputFieldName, list[ExpectedToolFieldValue]] = Field(
        default_factory=dict[ToolInputFieldName, list[ExpectedToolFieldValue]]
    )


class RequiredFactGroup(ImmutableDTO):
    """A fact the replies must name, written in any of `values`."""

    values: list[RequiredReplyFact]


class EvalExpectations(ImmutableDTO):
    """
    Everything the deterministic scorers check in one scenario besides the
    reply language (which the scenario itself names).

    `is_handoff_expected` None leaves the handoff criterion out.
    """

    tool_calls: list[ExpectedToolCall] = Field(default_factory=list[ExpectedToolCall])
    forbidden_tools: list[AssistantToolName] = Field(
        default_factory=list[AssistantToolName]
    )
    prices: list[Money] = Field(default_factory=list[Money])
    required_facts: list[RequiredFactGroup] = Field(
        default_factory=list[RequiredFactGroup]
    )
    forbidden_values: list[ForbiddenReplyValue] = Field(
        default_factory=list[ForbiddenReplyValue]
    )
    is_handoff_expected: IsHandoffExpected | None = None


class EvalCriterionResult(ImmutableDTO):
    """One criterion of one scenario: passed, or failed with its reasons."""

    criterion: EvalCriterion
    is_passed: IsEvalCriterionPassed
    notes: list[EvalCheckNote] = Field(default_factory=list[EvalCheckNote])

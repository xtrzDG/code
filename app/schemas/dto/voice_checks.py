"""
The voice checks of autotests: simulated calls against an agent built from
the version under test, in each of its languages.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.voice_checks import VoiceCheckStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.channels.strings import CallLocalTimeText, CallNextDaysText
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.voice.strings import (
    VoiceCheckBrief,
    VoiceCheckCondition,
    VoiceCheckRationale,
)


class VoiceToolMock(ImmutableDTO):
    """What a tool answers in a simulated call (no tool really runs)."""

    tool_name: AssistantToolName
    result_json: LlmToolResultJson


class VoiceCheckCallContext(ImmutableDTO):
    """The "Current call" lines a simulated call starts with."""

    local_now_text: CallLocalTimeText
    next_days_text: CallNextDaysText
    timezone: TimezoneName


class VoiceCheckCase(ImmutableDTO):
    """
    One simulated call: the caller's brief, in `language`, what the call
    must show to pass, its date context and what each tool answers.
    """

    key: AutotestScenarioKey
    language: LanguageTag
    brief: VoiceCheckBrief
    condition: VoiceCheckCondition
    call_context: VoiceCheckCallContext
    tool_mocks: list[VoiceToolMock] = Field(default_factory=list[VoiceToolMock])


class VoiceCheckBatch(ImmutableDTO):
    """
    The simulated calls of one autotest run and the agent they talk to (the
    version under test; each call speaks to it in the call's language).
    """

    agent: VoiceAgentSpec
    cases: list[VoiceCheckCase]


class VoiceCheckLine(ImmutableDTO):
    """One line of a simulated call."""

    author: MessageAuthor
    text: MessageText


class VoiceCheckToolCall(ImmutableDTO):
    """A tool the agent called in a simulated call, with its arguments."""

    tool_name: AssistantToolName
    input_json: LlmToolInputJson


class VoiceCheckOutcome(ImmutableDTO):
    """How one simulated call went, as the voice platform reported it."""

    key: AutotestScenarioKey
    status: VoiceCheckStatus
    lines: list[VoiceCheckLine] = Field(default_factory=list[VoiceCheckLine])
    tool_calls: list[VoiceCheckToolCall] = Field(
        default_factory=list[VoiceCheckToolCall]
    )
    rationale: list[VoiceCheckRationale] = Field(
        default_factory=list[VoiceCheckRationale]
    )
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)


class VoiceCheckRun(ImmutableDTO):
    """Play the voice scenarios of a started autotest run."""

    run_id: AutotestRunId
    business: BusinessDocument
    version: AssistantVersionDocument
    scenarios: list[AutotestScenario]
    customer_phone_number: E164PhoneNumber | None = None

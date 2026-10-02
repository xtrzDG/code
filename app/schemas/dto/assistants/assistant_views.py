"""Views of assistant versions and autotest runs returned to the cabinet."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestRunStatus,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.assistants.booleans import (
    IsAutotestRunPassed,
    IsFullAutotestCoverage,
)
from app.schemas.typings.assistants.constrained_floats import (
    AutotestPassRate,
    AverageJudgeScore,
)
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    AutotestScenarioCount,
    JudgeScore,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId, AutotestRunId
from app.schemas.typings.assistants.strings import (
    AutotestCheckNote,
    JudgeNote,
    SystemPromptText,
    VoiceAgentId,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue


class BusinessFactView(ImmutableDTO):
    """One row of the fact table the assistant answers from."""

    key: FactKey
    label: FactLabel
    value: FactValue


class AssistantVersionSummary(ImmutableDTO):
    """An assistant version in the version history."""

    id: AssistantVersionId
    business_id: BusinessId
    version_number: AssistantVersionNumber
    status: AssistantVersionStatus
    niche_key: NicheKey
    model_id: LlmModelId
    tools: list[AssistantToolName]
    languages: list[LanguageTag]
    default_language: LanguageTag
    is_voice_enabled: IsVoiceEnabled
    profile_revision: Microseconds
    voice_agent_id: VoiceAgentId | None = None
    test_score: AverageJudgeScore | None = None
    autotest_run_id: AutotestRunId | None = None
    published_at: Microseconds | None = None
    created_at: Microseconds


class AssistantVersionDetails(AssistantVersionSummary):
    """
    An assistant version with its frozen instructions and fact table: the
    chat instruction, and the phone instruction of a version with voice
    (None for a version without voice or assembled before it existed).
    """

    prompt_text: SystemPromptText
    phone_prompt_text: SystemPromptText | None = None
    facts: list[BusinessFactView]


class JudgeCriterionScoreView(ImmutableDTO):
    """Judge score of one criterion."""

    criterion: JudgeCriterion
    score: JudgeScore


class AutotestTranscriptLineView(ImmutableDTO):
    """One line of an autotest conversation."""

    author: MessageAuthor
    text: MessageText


class AutotestScenarioResultView(ImmutableDTO):
    """Result of one autotest scenario."""

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    scores: list[JudgeCriterionScoreView]
    judge_notes: list[JudgeNote]
    check_notes: list[AutotestCheckNote]
    transcript: list[AutotestTranscriptLineView]
    cost_micro_usd: CostMicroUsd


class AutotestRunView(ImmutableDTO):
    """
    An autotest run with the status its version got.

    The run passes when every price and booking scenario passed and the
    average judge score is at least 4 of 5; only a passed run that covered
    every language and scenario kind (`is_full_coverage`) makes the version
    READY. While `status` is RUNNING the worker is still playing it:
    `scenario_count` is then the number of planned scenarios and `results`
    holds the ones finished so far (progress = results / scenario_count).
    """

    id: AutotestRunId
    business_id: BusinessId
    assistant_version_id: AssistantVersionId
    status: AutotestRunStatus
    is_full_coverage: IsFullAutotestCoverage
    version_status: AssistantVersionStatus
    scenario_count: AutotestScenarioCount
    passed_count: AutotestScenarioCount
    pass_rate: AutotestPassRate
    average_score: AverageJudgeScore | None = None
    is_passed: IsAutotestRunPassed
    cost_micro_usd: CostMicroUsd
    results: list[AutotestScenarioResultView]
    created_at: Microseconds
    updated_at: Microseconds

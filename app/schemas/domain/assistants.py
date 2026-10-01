from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.assistants.booleans import IsAutotestRunPassed
from app.schemas.typings.assistants.constrained_floats import (
    AutotestPassRate,
    AverageJudgeScore,
)
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    JudgeScore,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
from app.schemas.typings.assistants.strings import (
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


class BusinessFact(PersistentDocument):
    """One row of the fact table the assistant answers from."""

    key: FactKey
    label: FactLabel
    value: FactValue


class AssistantVersionDocument(BaseDocument):
    """
    Immutable result of assembling the profile with a niche template
    (concept table `assistant_versions`). Every edit creates a new version;
    rollback publishes an earlier one.
    """

    id: AssistantVersionId = Field(default_factory=AssistantVersionId)
    business_id: BusinessId
    version_number: AssistantVersionNumber
    status: AssistantVersionStatus = AssistantVersionStatus.DRAFT
    niche_key: NicheKey
    model_id: LlmModelId
    prompt_text: SystemPromptText
    tools: list[AssistantToolName]
    languages: list[LanguageTag]
    default_language: LanguageTag
    is_voice_enabled: IsVoiceEnabled
    facts: list[BusinessFact]
    profile_revision: Microseconds
    voice_agent_id: VoiceAgentId | None = None
    test_score: AverageJudgeScore | None = None
    autotest_run_id: AutotestRunId | None = None
    published_at: Microseconds | None = None


class AutotestTranscriptLine(PersistentDocument):
    """One line of an autotest conversation."""

    author: MessageAuthor
    text: MessageText


class JudgeCriterionScore(PersistentDocument):
    """Judge score for one of the five criteria."""

    criterion: JudgeCriterion
    score: JudgeScore


class AutotestScenarioResult(PersistentDocument):
    """Result of one scenario in one language (concept table `test_runs`)."""

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    scores: list[JudgeCriterionScore] = Field(default_factory=list[JudgeCriterionScore])
    judge_notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])
    transcript: list[AutotestTranscriptLine] = Field(
        default_factory=list[AutotestTranscriptLine]
    )
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)


class AutotestRunDocument(BaseDocument):
    """All scenario results for one assistant version."""

    id: AutotestRunId = Field(default_factory=AutotestRunId)
    business_id: BusinessId
    assistant_version_id: AssistantVersionId
    results: list[AutotestScenarioResult] = Field(
        default_factory=list[AutotestScenarioResult]
    )
    pass_rate: AutotestPassRate
    average_score: AverageJudgeScore | None = None
    is_passed: IsAutotestRunPassed

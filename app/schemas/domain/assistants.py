from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
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
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
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


class BusinessFact(PersistentDocument):
    """One row of the fact table the assistant answers from."""

    key: FactKey
    label: FactLabel
    value: FactValue


class AssistantVersionDocument(BaseDocument):
    """
    Immutable result of assembling the profile with a niche template
    (concept table `assistant_versions`). Every edit creates a new version;
    rollback publishes an earlier one. A version that never went live is
    discarded (`discarded_at`) once a newer one does: it leaves the list of
    versions but stays readable, since test chats may still point to it.
    """

    # 2: `phone_prompt_text` (optional, so version 1 needs no upcaster).
    # 3: `discarded_at` (optional: a version stored before is not discarded).
    schema_version: SchemaVersion = SchemaVersion("3")
    id: AssistantVersionId = Field(default_factory=AssistantVersionId)
    business_id: BusinessId
    version_number: AssistantVersionNumber
    status: AssistantVersionStatus = AssistantVersionStatus.DRAFT
    niche_key: NicheKey
    model_id: LlmModelId
    prompt_text: SystemPromptText
    # The voice agent's instruction (spoken facts, no links); None for a
    # version assembled before it existed, whose agent uses `prompt_text`.
    phone_prompt_text: SystemPromptText | None = None
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
    discarded_at: Microseconds | None = None


class AutotestTranscriptLine(PersistentDocument):
    """One line of an autotest conversation."""

    author: MessageAuthor
    text: MessageText


class JudgeCriterionScore(PersistentDocument):
    """Judge score for one of the five criteria."""

    criterion: JudgeCriterion
    score: JudgeScore


class AutotestScenarioResult(PersistentDocument):
    """
    Result of one scenario in one language (concept table `test_runs`).

    `check_notes` come from the test harness: failed deterministic checks
    (no booking created, no handoff, reply in another language) and why an
    ERRORED scenario could not be evaluated. The judge explains its scores
    in `judge_notes`.
    """

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    scores: list[JudgeCriterionScore] = Field(default_factory=list[JudgeCriterionScore])
    judge_notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])
    check_notes: list[AutotestCheckNote] = Field(
        default_factory=list[AutotestCheckNote]
    )
    transcript: list[AutotestTranscriptLine] = Field(
        default_factory=list[AutotestTranscriptLine]
    )
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)


class AutotestRunDocument(BaseDocument):
    """
    One autotest run of an assistant version and its scenario results.

    It is stored RUNNING when it starts (the worker plays it) with the number
    of planned scenarios; the worker stores the results so far after every
    scenario, so the cabinet can show progress, and all of them when
    FINISHED. `languages` and `kinds` are what the owner asked
    for (None means all); `is_full_coverage` is True when the run covered
    every version language and every applicable scenario kind, the only
    kind of run that can make a version READY. `previous_version_status`
    is the version's status before the run, restored when the run errors.
    """

    id: AutotestRunId = Field(default_factory=AutotestRunId)
    business_id: BusinessId
    assistant_version_id: AssistantVersionId
    status: AutotestRunStatus = AutotestRunStatus.FINISHED
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None
    is_full_coverage: IsFullAutotestCoverage = False
    planned_scenario_count: AutotestScenarioCount | None = None
    previous_version_status: AssistantVersionStatus | None = None
    results: list[AutotestScenarioResult] = Field(
        default_factory=list[AutotestScenarioResult]
    )
    pass_rate: AutotestPassRate = AutotestPassRate(0.0)
    average_score: AverageJudgeScore | None = None
    is_passed: IsAutotestRunPassed = False

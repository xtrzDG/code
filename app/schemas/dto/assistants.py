from base_pydantic_schemas import ImmutableDTO
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
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
    AutotestScenarioResult,
    BusinessFact,
    JudgeCriterionScore,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.assistants.booleans import (
    AcceptsFailedAutotests,
    IsAutotestRunPassed,
    IsFullAutotestCoverage,
    ShouldRunAutotests,
)
from app.schemas.typings.assistants.constrained_floats import (
    AutotestPassRate,
    AverageJudgeScore,
)
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    AutotestScenarioCount,
    JudgeScore,
    LlmPricePerMillionTokensMicroUsd,
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
    AutotestScenarioGoal,
    JudgeNote,
    SystemPromptText,
    VoiceAgentId,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from app.schemas.typings.users.prefixed_id import UserId

# HTTP bodies and commands.


class AssembleAssistantVersionRequest(ImmutableDTO):
    """
    HTTP body of version assembly; every field is optional.

    `languages` and `kinds` only narrow the autotests that run right after
    the assembly; the version itself always covers every business language.
    """

    run_autotests: ShouldRunAutotests = True
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None


class AssembleAssistantVersionCommand(ImmutableDTO):
    """Owner assembles a new assistant version from the current profile."""

    user_id: UserId
    business_id: BusinessId
    request: AssembleAssistantVersionRequest = Field(
        default_factory=AssembleAssistantVersionRequest
    )


class AssistantVersionsQuery(ImmutableDTO):
    """List the assistant versions of a business (owners and staff)."""

    user_id: UserId
    business_id: BusinessId


class AssistantVersionQuery(ImmutableDTO):
    """Read one assistant version (owners and staff)."""

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId


class RunAutotestsRequest(ImmutableDTO):
    """HTTP body of an autotest run; missing lists mean "all of them"."""

    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None


class RunAutotestsCommand(ImmutableDTO):
    """Owner runs the autotests of one version, optionally narrowed."""

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None


class PublishAssistantVersionRequest(ImmutableDTO):
    """
    HTTP body of publishing. A version that did not pass the autotests is
    published only by a platform admin with `accept_failed_tests` set (the
    decision is written to the audit log).
    """

    accept_failed_tests: AcceptsFailedAutotests = False


class PublishAssistantVersionCommand(ImmutableDTO):
    """Owner switches the assistant to a version ("Включить")."""

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId
    accept_failed_tests: AcceptsFailedAutotests = False


class RollbackAssistantVersionCommand(ImmutableDTO):
    """Owner publishes an earlier, archived version again."""

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId


# Views returned to the cabinet.


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
    """An assistant version with its frozen instruction and fact table."""

    prompt_text: SystemPromptText
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
    READY. While `status` is RUNNING the worker is still playing it.
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


# Internal inputs of transformers and use cases.


class BusinessFactsSource(ImmutableDTO):
    """
    Everything the fact table is built from.

    `today` is the business-local date of the assembly; only schedule
    exceptions from that day on are listed.
    """

    business: BusinessDocument
    profile: BusinessProfileDocument
    niche: NicheTemplate
    country: CountryProfile
    language_profiles: list[LanguageProfile]
    knowledge_items: list[KnowledgeItemDocument]
    resources: list[ResourceDocument]
    schedule_exceptions: list[ScheduleExceptionDocument]
    today: LocalDate


class AssistantInstructionSource(ImmutableDTO):
    """Everything the instruction (system prompt) of a version is composed from."""

    business: BusinessDocument
    profile: BusinessProfileDocument
    niche: NicheTemplate
    country: CountryProfile
    language_profiles: list[LanguageProfile]
    facts: list[BusinessFact]
    tools: list[AssistantToolName]


class AutotestLanguage(ImmutableDTO):
    """A language scenarios are written in, with its English name and script."""

    tag: LanguageTag
    name: LanguageDisplayName
    script: ScriptCode | None = None


class AutotestScenario(ImmutableDTO):
    """
    One scripted test conversation: what the AI customer tries, in which
    language. `language_script` is None when the script is unknown, which
    turns the reply-language check off.
    """

    key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    language_name: LanguageDisplayName
    language_script: ScriptCode | None = None
    goal: AutotestScenarioGoal


class AutotestRunPlan(ImmutableDTO):
    """
    A started autotest run: the version under test and its scenarios.

    `is_full_coverage` tells whether the scenarios cover every version
    language and applicable kind; `previous_version_status` is the status
    the version had before the run. An empty `scenarios` list means there
    is nothing left to run (the run already finished).
    """

    run_id: AutotestRunId
    business: BusinessDocument
    version: AssistantVersionDocument
    scenarios: list[AutotestScenario]
    is_full_coverage: IsFullAutotestCoverage
    previous_version_status: AssistantVersionStatus
    customer_phone_number: E164PhoneNumber | None = None
    started_at: Microseconds


class AutotestPlanningRequest(ImmutableDTO):
    """Scenarios to plan for a version; missing lists mean "all of them"."""

    business: BusinessDocument
    version: AssistantVersionDocument
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None


class AutotestScenarioPlanning(ImmutableDTO):
    """Planned scenarios and whether they cover everything a launch needs."""

    scenarios: list[AutotestScenario]
    is_full_coverage: IsFullAutotestCoverage


class AutotestJobPayload(ImmutableDTO):
    """Payload of the queued job that plays a started autotest run."""

    run_id: AutotestRunId


class AutotestRunFailure(ImmutableDTO):
    """A queued autotest run that could not be completed."""

    business_id: BusinessId
    run_id: AutotestRunId


class AutotestScenarioRun(ImmutableDTO):
    """Run one scenario of a started run against the version under test."""

    run_id: AutotestRunId
    business: BusinessDocument
    version: AssistantVersionDocument
    scenario: AutotestScenario
    customer_phone_number: E164PhoneNumber | None = None


class AutotestRunCompletion(ImmutableDTO):
    """Scenario results of a run, ready to be evaluated and stored."""

    plan: AutotestRunPlan
    results: list[AutotestScenarioResult]


class AutotestRunSummary(ImmutableDTO):
    """Thresholds applied to the scenario results of one run."""

    scenario_count: AutotestScenarioCount
    passed_count: AutotestScenarioCount
    pass_rate: AutotestPassRate
    average_score: AverageJudgeScore | None = None
    is_passed: IsAutotestRunPassed


class AutotestRunViewSource(ImmutableDTO):
    """A stored run together with the current state of its version."""

    run: AutotestRunDocument
    version: AssistantVersionDocument


class JudgeVerdict(ImmutableDTO):
    """Parsed answer of the judge: one score per criterion and its reasons."""

    scores: list[JudgeCriterionScore]
    notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])


class AssistantVersionActivation(ImmutableDTO):
    """Publish an authorized version of an authorized business."""

    business: BusinessDocument
    version: AssistantVersionDocument


class LlmTokenPrice(ImmutableDTO):
    """List price of one model, used to estimate the cost of test calls."""

    model_id: LlmModelId
    input_price: LlmPricePerMillionTokensMicroUsd
    output_price: LlmPricePerMillionTokensMicroUsd

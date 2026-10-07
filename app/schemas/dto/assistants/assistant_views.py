"""Views of assistant versions and autotest runs returned to the cabinet."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestCheckCode,
    AutotestExpectation,
    AutotestOutcome,
    AutotestRunStatus,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.assistants.autotest_comparison_views import (
    AutotestRunComparisonView,
)
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
    AutotestPassedSampleCount,
    AutotestSampleCount,
    AutotestScenarioCount,
    JudgeScore,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestCaseId,
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
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
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


class OwnerCheckAskedView(ImmutableDTO):
    """What an owner check asked when it was played: its question and expectation."""

    question: AutotestCaseQuestion
    expectation: AutotestExpectation
    expected_text: AutotestExpectedText | None = None


class AutotestScenarioResultView(ImmutableDTO):
    """
    Result of one autotest scenario. An owner check names its check and
    what it asked (`owner_check`; None for results stored before);
    `conversation_id` and `answer_message_id` are the test conversation and
    the assistant's first answer in it ("Fix this answer" opens it).
    """

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    scores: list[JudgeCriterionScoreView]
    judge_notes: list[JudgeNote]
    check_notes: list[AutotestCheckNote]
    check_codes: list[AutotestCheckCode] = Field(
        default_factory=list[AutotestCheckCode]
    )
    transcript: list[AutotestTranscriptLineView]
    cost_micro_usd: CostMicroUsd
    # The owner's check an OWNER_CHECK scenario played.
    autotest_case_id: AutotestCaseId | None = None
    # pass^k: how often a launch-critical scenario was played and how many
    # of its plays passed (None: played once).
    sample_count: AutotestSampleCount | None = None
    passed_sample_count: AutotestPassedSampleCount | None = None
    owner_check: OwnerCheckAskedView | None = None
    conversation_id: ConversationId | None = None
    answer_message_id: MessageId | None = None


class AutotestRunView(ImmutableDTO):
    """
    An autotest run with the status its version got.

    The run passes when every price and booking scenario passed and the
    average judge score is at least 4 of 5; only a passed run that covered
    every language and scenario kind (`is_full_coverage`) makes the version
    READY. While `status` is RUNNING the worker is still playing it:
    `scenario_count` is then the number of planned scenarios and `results`
    holds the ones finished so far (progress = results / scenario_count).
    `comparison` sets a finished run against the run of the version that
    was live when it started (None when nothing was live then).
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
    comparison: AutotestRunComparisonView | None = None
    created_at: Microseconds
    updated_at: Microseconds

from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestCheckCode,
    AutotestOutcome,
    AutotestRunStatus,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.autotest_cases import OwnerCheckSnapshot
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
from app.schemas.typings.profiles.booleans import IsImportedFact
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue


class BusinessFact(PersistentDocument):
    """
    One row of the fact table the assistant answers from. `is_imported`:
    the row describes knowledge imported from a website or a menu file, so
    the instruction shows its value as an untrusted block.
    """

    key: FactKey
    label: FactLabel
    value: FactValue
    is_imported: IsImportedFact = False


class AutotestVerdict(PersistentDocument):
    """
    The verdict of the latest finished autotest run of a version, stored on
    the version when the run finishes: the one place every screen reads
    "passed or not" from (the version page, the platform admin, go-live).
    `scenario_count - passed_count` scenarios failed; a run can pass with
    a few of them failed (concept section 11: every price and booking
    scenario passed and an average judge score of at least 4).
    """

    run_id: AutotestRunId
    is_passed: IsAutotestRunPassed
    scenario_count: AutotestScenarioCount
    passed_count: AutotestScenarioCount
    average_score: AverageJudgeScore | None = None
    is_full_coverage: IsFullAutotestCoverage = False
    finished_at: Microseconds


class AssistantVersionDocument(BaseDocument):
    """
    Immutable result of assembling the profile with a niche template
    (concept table `assistant_versions`). Every edit creates a new version;
    rollback publishes an earlier one. A version that never went live is
    discarded (`discarded_at`) once a newer one does: it leaves the list of
    versions but stays readable, since test chats may still point to it.
    """

    # 2: `phone_prompt_text` (optional, so version 1 needs no upcaster).
    # 3: `autotest_verdict` (optional: a version tested before it existed
    #    has none, and readers fall back to its status).
    # 4: `discarded_at` (optional: a version stored before is not discarded).
    # 5: `facts[].is_imported` (optional: older facts read as written by
    #    the owner).
    # 6: the tool list_my_bookings in `tools` (a new value, no upcaster).
    # 7: the tool join_waitlist in `tools` (a new value, no upcaster).
    # 8: the tool offer_choices may appear in `tools` once its release gate
    #    is open (a new value, no upcaster).
    schema_version: SchemaVersion = SchemaVersion("8")
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
    autotest_verdict: AutotestVerdict | None = None
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
    ERRORED scenario could not be evaluated; `check_codes` say the same as
    codes every language renders (empty on results stored before codes
    existed). The judge explains its scores in `judge_notes`. An owner
    check's result names its check (`autotest_case_id`) and keeps what it
    asked (`owner_check`). `conversation_id` and `answer_message_id` are
    the test conversation and the assistant's first answer in it, so the
    owner can fix that answer.
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
    check_codes: list[AutotestCheckCode] = Field(
        default_factory=list[AutotestCheckCode]
    )
    transcript: list[AutotestTranscriptLine] = Field(
        default_factory=list[AutotestTranscriptLine]
    )
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)
    autotest_case_id: AutotestCaseId | None = None
    sample_count: AutotestSampleCount | None = None
    passed_sample_count: AutotestPassedSampleCount | None = None
    owner_check: OwnerCheckSnapshot | None = None
    conversation_id: ConversationId | None = None
    answer_message_id: MessageId | None = None


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
    `compared_to_run_id` is the run of the version that was live when this
    run started (None when nothing was live or this version is the live
    one): the version page shows new failures and score changes against it.
    """

    # 2: `check_codes` on the scenario results (optional, no upcaster).
    # 3: the language scenario kinds (foreign_language, transliterated) and
    # the wrong_disclosure_language check code (new values, no upcaster).
    # 4: owner checks: the owner_check kind, its three check codes and the
    # `autotest_case_id` of their results (new values and an optional
    # field, no upcaster).
    # 5: pass^k (`sample_count`, `passed_sample_count` on the results), the
    # four attack kinds, the price and attack check codes, and
    # `compared_to_run_id` (new values and optional fields, no upcaster).
    # 6: what an owner check asked (`owner_check`) and the test conversation
    # of a result (`conversation_id`, `answer_message_id`) (optional fields,
    # no upcaster).
    schema_version: SchemaVersion = SchemaVersion("6")
    id: AutotestRunId = Field(default_factory=AutotestRunId)
    business_id: BusinessId
    assistant_version_id: AssistantVersionId
    status: AutotestRunStatus = AutotestRunStatus.FINISHED
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None
    is_full_coverage: IsFullAutotestCoverage = False
    planned_scenario_count: AutotestScenarioCount | None = None
    previous_version_status: AssistantVersionStatus | None = None
    compared_to_run_id: AutotestRunId | None = None
    results: list[AutotestScenarioResult] = Field(
        default_factory=list[AutotestScenarioResult]
    )
    pass_rate: AutotestPassRate = AutotestPassRate(0.0)
    average_score: AverageJudgeScore | None = None
    is_passed: IsAutotestRunPassed = False

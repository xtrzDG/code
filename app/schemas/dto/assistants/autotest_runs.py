"""
Internal inputs and results of autotest runs: plans, scenarios, progress,
verdicts and summaries.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestScenarioKind,
)
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
    AutotestScenarioResult,
    JudgeCriterionScore,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.smoke_checks import SmokeCheckSelection
from app.schemas.typings.assistants.booleans import (
    IsAutotestRunPassed,
    IsFullAutotestCoverage,
)
from app.schemas.typings.assistants.constrained_floats import (
    AutotestPassRate,
    AverageJudgeScore,
)
from app.schemas.typings.assistants.constrained_integers import AutotestScenarioCount
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.schemas.typings.assistants.strings import AutotestScenarioGoal, JudgeNote
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName


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
    language and applicable kind; `smoke_check` is set for the quick check
    of an apply, whose pass makes the version ready as a full run's does;
    `previous_version_status` is the status the version had before the
    run. An empty `scenarios` list means there is nothing left to run (the
    run already finished).
    """

    run_id: AutotestRunId
    business: BusinessDocument
    version: AssistantVersionDocument
    scenarios: list[AutotestScenario]
    is_full_coverage: IsFullAutotestCoverage
    smoke_check: SmokeCheckSelection | None = None
    previous_version_status: AssistantVersionStatus
    customer_phone_number: E164PhoneNumber | None = None
    started_at: Microseconds


class AutotestPlanningRequest(ImmutableDTO):
    """
    Scenarios to plan for a version; missing lists mean "all of them", and
    a `smoke_check` plans exactly its scenarios instead.
    """

    business: BusinessDocument
    version: AssistantVersionDocument
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None
    smoke_check: SmokeCheckSelection | None = None


class AutotestScenarioPlanning(ImmutableDTO):
    """Planned scenarios and whether they cover everything a launch needs."""

    scenarios: list[AutotestScenario]
    is_full_coverage: IsFullAutotestCoverage


class AutotestJobPayload(ImmutableDTO):
    """
    Payload of the queued job that plays a started autotest run; the quick
    check of an apply carries its scenarios, so the worker plays the same.
    """

    run_id: AutotestRunId
    smoke_check: SmokeCheckSelection | None = None


class AutotestRunProgress(ImmutableDTO):
    """Results of the scenarios a running autotest run finished so far."""

    business_id: BusinessId
    run_id: AutotestRunId
    results: list[AutotestScenarioResult]


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

"""Go-live checklist of an assistant version (concept section 4, "Проверка")."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestRunStatus,
    GoLiveCheckCode,
)
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.assistants.booleans import (
    IsAutotestRunPassed,
    IsFullAutotestCoverage,
    IsGoLiveCheckBlocking,
    IsGoLiveCheckPassed,
    IsReadyToGoLive,
)
from app.schemas.typings.assistants.constrained_floats import (
    AutotestPassRate,
    AverageJudgeScore,
)
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    AutotestScenarioCount,
)
from app.schemas.typings.assistants.constrained_strings import GoLiveCheckDetail
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
from app.schemas.typings.assistants.strings import GoLiveCheckMessage
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion


class GoLiveReadinessRequest(ImmutableDTO):
    """Check whether an authorized business may make this version live."""

    business: BusinessDocument
    version: AssistantVersionDocument


class GoLiveCheck(ImmutableDTO):
    """
    One launch condition and what was found.

    A failed `is_blocking` check stops publishing; a failed non-blocking one
    is only a warning (voice without ElevenLabs in development). `details`
    qualify it by code:

    - subscription_or_trial: the subscription status, or "none";
    - dpa: the agreement version to accept;
    - profile_gaps: the blocking gap kinds ("no_opening_hours", ...);
    - staff_contact: "no_handoff_contact" while nobody receives handoffs;
    - autotests: the version status, then the latest run's status;
    - voice_configuration: the missing server settings ("APP_BASE_URL").
    """

    code: GoLiveCheckCode
    is_ok: IsGoLiveCheckPassed
    is_blocking: IsGoLiveCheckBlocking
    message: GoLiveCheckMessage
    details: list[GoLiveCheckDetail] = Field(default_factory=list[GoLiveCheckDetail])


class GoLiveAutotestRunSummary(ImmutableDTO):
    """The version's latest autotest run as the checklist reports it."""

    id: AutotestRunId
    status: AutotestRunStatus
    is_full_coverage: IsFullAutotestCoverage
    is_passed: IsAutotestRunPassed
    scenario_count: AutotestScenarioCount
    passed_count: AutotestScenarioCount
    pass_rate: AutotestPassRate
    average_score: AverageJudgeScore | None = None
    updated_at: Microseconds


class GoLiveReadiness(ImmutableDTO):
    """
    Every go-live check of one version, in a fixed order: subscription or
    trial, data processing agreement, profile gaps, staff contact,
    autotests, then voice configuration (only for versions with voice).

    `is_ready` is True when no blocking check failed: then an owner can
    publish the version. The same checks guard publishing and rollback, and
    their codes name the reasons of a refusal.
    """

    business_id: BusinessId
    assistant_version_id: AssistantVersionId
    version_number: AssistantVersionNumber
    version_status: AssistantVersionStatus
    is_ready: IsReadyToGoLive
    checks: list[GoLiveCheck]
    autotest_run: GoLiveAutotestRunSummary | None = None
    subscription_status: SubscriptionStatus | None = None
    dpa_document_version: DpaDocumentVersion

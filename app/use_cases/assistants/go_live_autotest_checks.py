"""The autotest check of going live, and the run it is based on."""

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestOutcome,
    GoLiveCheckCode,
)
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.dto.go_live import (
    GoLiveAutotestRunSummary,
    GoLiveCheck,
)
from app.schemas.typings.assistants.constrained_integers import AutotestScenarioCount
from app.schemas.typings.assistants.constrained_strings import GoLiveCheckDetail
from app.schemas.typings.assistants.strings import GoLiveCheckMessage
from app.utilities.assembly.autotest_evaluation import count_run_scenarios

PARTIAL_COVERAGE_DETAIL: str = "partial_coverage"

# Versions that may go live as far as the autotests are concerned: READY
# passed them, a PUBLISHED or ARCHIVED one was live already (rollback).
AUTOTESTS_OK_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {
        AssistantVersionStatus.READY,
        AssistantVersionStatus.PUBLISHED,
        AssistantVersionStatus.ARCHIVED,
    }
)


def check_autotests(
    version: AssistantVersionDocument,
    run: AutotestRunDocument | None,
) -> GoLiveCheck:
    """Passed autotests: a READY version (or one that was live already)."""

    details: list[GoLiveCheckDetail] = [GoLiveCheckDetail(version.status.value)]
    if run is not None:
        details.append(GoLiveCheckDetail(run.status.value))
        if not run.is_full_coverage:
            details.append(GoLiveCheckDetail(PARTIAL_COVERAGE_DETAIL))

    number: int = int(version.version_number)
    message: str
    match version.status:
        case AssistantVersionStatus.READY:
            message = f"Version {number} passed its autotests."
        case AssistantVersionStatus.PUBLISHED:
            message = f"Version {number} is live."
        case AssistantVersionStatus.ARCHIVED:
            message = f"Version {number} was live before."
        case AssistantVersionStatus.TESTING:
            message = (
                f"Version {number} is being tested; publish it when the "
                "autotests finish."
            )
        case AssistantVersionStatus.DRAFT | AssistantVersionStatus.TESTS_FAILED:
            message = (
                f"Version {number} has not passed the autotests (status "
                f"{version.status.value}). Run the autotests in every language "
                "and publish it when it is ready."
            )

    return GoLiveCheck(
        code=GoLiveCheckCode.AUTOTESTS,
        is_ok=version.status in AUTOTESTS_OK_STATUSES,
        is_blocking=True,
        message=GoLiveCheckMessage(message),
        details=details,
    )


def summarize_autotest_run(run: AutotestRunDocument) -> GoLiveAutotestRunSummary:
    return GoLiveAutotestRunSummary(
        id=run.id,
        status=run.status,
        is_full_coverage=run.is_full_coverage,
        is_passed=run.is_passed,
        scenario_count=count_run_scenarios(run),
        completed_count=AutotestScenarioCount(len(run.results)),
        passed_count=AutotestScenarioCount(
            sum(1 for result in run.results if result.outcome is AutotestOutcome.PASSED)
        ),
        pass_rate=run.pass_rate,
        average_score=run.average_score,
        updated_at=run.updated_at,
    )

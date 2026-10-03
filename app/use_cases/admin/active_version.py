"""The assistant version the platform admin judges a client by, and its verdict."""

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestVerdict
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.admin import ClientAutotestVerdict
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.schemas.typings.client_health.constrained_integers import (
    AutotestFailureCount,
)


def find_active_version(
    version_repo: AssistantVersionRepoContract,
    business: BusinessDocument,
) -> AssistantVersionDocument | None:
    """
    The version that speaks for the client: the published one, else the
    newest version that was tested (None when nothing was).
    """

    if business.published_assistant_version_id is not None:
        published: AssistantVersionDocument | None = version_repo.get(
            business.id, business.published_assistant_version_id
        )
        if published is not None:
            return published

    tested_versions: list[AssistantVersionDocument] = [
        version
        for version in version_repo.list_by_business(business.id)
        if version.autotest_verdict is not None
        or version.autotest_run_id is not None
        or version.test_score is not None
    ]
    if tested_versions == []:
        return None

    return max(tested_versions, key=lambda version: version.version_number)


def read_client_verdict(
    version: AssistantVersionDocument | None,
) -> ClientAutotestVerdict | None:
    """
    The verdict the version stores; for a version tested before verdicts
    were stored, its status (TESTS_FAILED or not) without counts. None for
    a version that was never tested.
    """

    if version is None:
        return None

    verdict: AutotestVerdict | None = version.autotest_verdict
    if verdict is not None:
        return ClientAutotestVerdict(
            version_number=version.version_number,
            is_passed=verdict.is_passed,
            passed_count=verdict.passed_count,
            scenario_count=verdict.scenario_count,
            average_score=verdict.average_score,
        )

    if version.autotest_run_id is None and version.test_score is None:
        return None

    return ClientAutotestVerdict(
        version_number=version.version_number,
        is_passed=version.status is not AssistantVersionStatus.TESTS_FAILED,
        average_score=version.test_score,
    )


def count_failed_scenarios(
    verdict: ClientAutotestVerdict | None,
) -> AutotestFailureCount:
    """Scenarios of the verdict's run that did not pass (0 when unknown)."""

    if verdict is None or verdict.scenario_count is None:
        return AutotestFailureCount(0)

    return AutotestFailureCount(
        int(verdict.scenario_count) - int(verdict.passed_count or 0)
    )


def find_verdict_run_id(
    version: AssistantVersionDocument | None,
) -> AutotestRunId | None:
    """The run the version's verdict comes from (its latest run without one)."""

    if version is None:
        return None

    if version.autotest_verdict is not None:
        return version.autotest_verdict.run_id

    return version.autotest_run_id

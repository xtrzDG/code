from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import (
    AutotestPlanningRequest,
    AutotestRunPlan,
    AutotestScenarioPlanning,
    RunAutotestsCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.utilities.assembly.fact_formatting import find_example_mobile_number

UNTESTABLE_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {AssistantVersionStatus.PUBLISHED, AssistantVersionStatus.ARCHIVED}
)


class StartAutotestRunUseCase(UseCaseContract[RunAutotestsCommand, AutotestRunPlan]):
    """
    Owner starts the autotests of a version (concept sections 4 and 11).

    The scenarios are planned (see PlanAutotestScenariosUseCase), the run is
    stored as RUNNING and the version moves to TESTING and points to it, so
    the cabinet can follow the run while it is played. Live and archived
    versions are not re-tested, because that would change their status, and
    a version already under test is not tested twice at once. The AI
    customer gets a valid example mobile number of the business country, so
    bookings work for any country.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        plan_autotest_scenarios: UseCaseContract[
            AutotestPlanningRequest,
            AutotestScenarioPlanning,
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._plan_autotest_scenarios: UseCaseContract[
            AutotestPlanningRequest,
            AutotestScenarioPlanning,
        ] = plan_autotest_scenarios
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RunAutotestsCommand) -> AutotestRunPlan:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id,
            input_data.version_id,
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {input_data.version_id} was not found."
            )

        if version.status in UNTESTABLE_STATUSES:
            raise ConflictError(
                f"Version {version.version_number} is {version.status.value}; "
                "assemble a new version to test changes."
            )

        if version.status is AssistantVersionStatus.TESTING:
            raise ConflictError(
                f"Version {version.version_number} is being tested; wait for "
                "the autotest run to finish."
            )

        planning: AutotestScenarioPlanning = self._plan_autotest_scenarios.run(
            AutotestPlanningRequest(
                business=business,
                version=version,
                languages=input_data.languages,
                kinds=input_data.kinds,
            )
        )
        if not planning.scenarios:
            raise ValidationFailedError("There are no autotest scenarios to run.")

        now: Microseconds = self._wall_clock.now_unix()
        previous_status: AssistantVersionStatus = version.status
        run = AutotestRunDocument(
            id=AutotestRunId(),
            business_id=business.id,
            assistant_version_id=version.id,
            status=AutotestRunStatus.RUNNING,
            languages=input_data.languages,
            kinds=input_data.kinds,
            is_full_coverage=planning.is_full_coverage,
            previous_version_status=previous_status,
            created_at=now,
            updated_at=now,
        )
        self._autotest_run_repo.save(run)
        version.status = AssistantVersionStatus.TESTING
        version.autotest_run_id = run.id
        version.updated_at = now
        self._assistant_version_repo.save(version)
        return AutotestRunPlan(
            run_id=run.id,
            business=business,
            version=version,
            scenarios=planning.scenarios,
            is_full_coverage=planning.is_full_coverage,
            previous_version_status=previous_status,
            customer_phone_number=find_example_mobile_number(business.country_code),
            started_at=now,
        )

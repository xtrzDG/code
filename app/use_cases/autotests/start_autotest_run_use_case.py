from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.dto.assistants.autotest_runs import (
    AutotestPlanningRequest,
    AutotestRunPlan,
    AutotestScenarioPlanning,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.constrained_integers import AutotestScenarioCount
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
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
    a version already under test is not tested twice at once. The quick
    check of "Apply changes" (`smoke_check`) records the languages and
    kinds it plays. The AI
    customer gets a valid example mobile number of the business country, so
    bookings work for any country. The run remembers the run of the version
    live at its start (`compared_to_run_id`) to show what changed against it.
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
        live_events: EventPublisherFacilitatorContract,
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
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: RunAutotestsCommand) -> AutotestRunPlan:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                # Done-for-you setup: support may, with the owner's consent.
                support_may_change=True,
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
                smoke_check=input_data.smoke_check,
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
            languages=(
                input_data.languages
                if input_data.smoke_check is None
                else list(dict.fromkeys(item.language for item in planning.scenarios))
            ),
            kinds=(
                input_data.kinds
                if input_data.smoke_check is None
                else list(dict.fromkeys(item.kind for item in planning.scenarios))
            ),
            is_full_coverage=planning.is_full_coverage,
            planned_scenario_count=AutotestScenarioCount(len(planning.scenarios)),
            previous_version_status=previous_status,
            compared_to_run_id=self._find_live_run_id(business, version),
            created_at=now,
            updated_at=now,
        )
        self._autotest_run_repo.save(run)
        version.status = AssistantVersionStatus.TESTING
        version.autotest_run_id = run.id
        version.updated_at = now
        self._assistant_version_repo.save(version)
        self._live_events.publish(
            run.business_id,
            LiveEventKind.AUTOTEST_PROGRESS,
            (run.id, run.assistant_version_id),
        )
        return AutotestRunPlan(
            run_id=run.id,
            business=business,
            version=version,
            scenarios=planning.scenarios,
            is_full_coverage=planning.is_full_coverage,
            smoke_check=input_data.smoke_check,
            previous_version_status=previous_status,
            customer_phone_number=find_example_mobile_number(business.country_code),
            started_at=now,
        )

    def _find_live_run_id(
        self, business: BusinessDocument, version: AssistantVersionDocument
    ) -> AutotestRunId | None:
        """The run whose verdict let the live version go live, if any."""

        live_id: AssistantVersionId | None = business.published_assistant_version_id
        if live_id is None or live_id == version.id:
            return None

        live: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, live_id
        )
        if live is None:
            return None

        if live.autotest_verdict is not None:
            return live.autotest_verdict.run_id

        return live.autotest_run_id

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.autotest_runs import (
    AutotestJobPayload,
    AutotestPlanningRequest,
    AutotestRunPlan,
    AutotestScenario,
    AutotestScenarioPlanning,
)
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.assembly.fact_formatting import find_example_mobile_number


class ResumeAutotestRunUseCase(UseCaseContract[QueuedJobInput, AutotestRunPlan]):
    """
    In the worker: rebuild the plan of a queued autotest run from the stored
    RUNNING run (the scenarios the owner asked for). A run that is no longer
    RUNNING (finished or given up) yields a plan without scenarios, so a
    repeated job changes nothing.

    Raises:
        ValidationFailedError: the job has no business or a broken payload.
        NotFoundError: the run, its version or its business is gone.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        plan_autotest_scenarios: UseCaseContract[
            AutotestPlanningRequest,
            AutotestScenarioPlanning,
        ],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._plan_autotest_scenarios: UseCaseContract[
            AutotestPlanningRequest,
            AutotestScenarioPlanning,
        ] = plan_autotest_scenarios

    def run(self, input_data: QueuedJobInput) -> AutotestRunPlan:
        business_id: BusinessId | None = input_data.business_id
        if business_id is None:
            raise ValidationFailedError("An autotest job must name its business.")

        payload: AutotestJobPayload = AutotestJobPayload.model_validate_json(
            str(input_data.payload)
        )
        run: AutotestRunDocument | None = self._autotest_run_repo.get(
            business_id,
            payload.run_id,
        )
        business: BusinessDocument | None = self._business_repo.get(business_id)
        if run is None or business is None:
            raise NotFoundError(f"Autotest run {payload.run_id} was not found.")

        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business_id,
            run.assistant_version_id,
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {run.assistant_version_id} was not found."
            )

        scenarios: list[AutotestScenario] = []
        if run.status is AutotestRunStatus.RUNNING:
            scenarios = self._plan_autotest_scenarios.run(
                AutotestPlanningRequest(
                    business=business,
                    version=version,
                    languages=run.languages,
                    kinds=run.kinds,
                    smoke_check=payload.smoke_check,
                )
            ).scenarios

        return AutotestRunPlan(
            run_id=run.id,
            business=business,
            version=version,
            scenarios=scenarios,
            is_full_coverage=run.is_full_coverage,
            smoke_check=payload.smoke_check,
            previous_version_status=(
                run.previous_version_status or AssistantVersionStatus.DRAFT
            ),
            customer_phone_number=find_example_mobile_number(business.country_code),
            started_at=run.created_at,
        )

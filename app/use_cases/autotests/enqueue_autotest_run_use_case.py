from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.assistant_repositories import AutotestRunRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import (
    AutotestJobPayload,
    AutotestRunPlan,
    AutotestRunViewSource,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson

RUN_AUTOTESTS_JOB: JobName = JobName("run_autotests")
AUTOTESTS_SERIAL_KEY_PREFIX: str = "autotests"


class EnqueueAutotestRunUseCase(UseCaseContract[AutotestRunPlan, AutotestRunView]):
    """
    Hand a started autotest run to the background worker (concept: the
    worker runs assembly autotests over the Postgres job queue). A run plays
    hundreds of model calls, far longer than an HTTP request may take; the
    owner gets the RUNNING run at once and follows it in the cabinet.
    """

    def __init__(
        self,
        autotest_run_repo: AutotestRunRepoContract,
        job_queue: JobQueueFacilitatorContract,
        autotest_run_view_transformer: TransformerContract[
            AutotestRunViewSource,
            AutotestRunView,
        ],
    ) -> None:
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._autotest_run_view_transformer: TransformerContract[
            AutotestRunViewSource,
            AutotestRunView,
        ] = autotest_run_view_transformer

    def run(self, input_data: AutotestRunPlan) -> AutotestRunView:
        run: AutotestRunDocument | None = self._autotest_run_repo.get(
            input_data.business.id,
            input_data.run_id,
        )
        if run is None:
            raise NotFoundError(f"Autotest run {input_data.run_id} was not found.")

        # The autotests lane, one run per business at a time: a long run
        # never delays customer messages or reminders, and one business
        # cannot take every autotest slot of the worker.
        self._job_queue.enqueue(
            RUN_AUTOTESTS_JOB,
            JobPayloadJson(AutotestJobPayload(run_id=run.id).model_dump_json()),
            input_data.business.id,
            lane=JobLane.AUTOTESTS,
            serial_key=JobSerialKey(
                f"{AUTOTESTS_SERIAL_KEY_PREFIX}:{input_data.business.id}"
            ),
        )
        return self._autotest_run_view_transformer.transform(
            AutotestRunViewSource(run=run, version=input_data.version)
        )

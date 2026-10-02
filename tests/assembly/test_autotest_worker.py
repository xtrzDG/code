"""Queued autotest runs in the background worker: playing, abandoning, progress."""

import pytest

from app.gateways.worker.background_worker import BackgroundWorker
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.assistants.run_queued_autotests_orchestrator import (
    RunQueuedAutotestsOrchestrator,
)
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.dto.assistants.assistant_commands import (
    AssistantVersionQuery,
    RunAutotestsCommand,
)
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import (
    AutotestRunCompletion,
    AutotestRunProgress,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.assembly.autotest_run_helpers import GEORGIAN_SCENARIO_COUNT, start
from tests.assembly.testbed import AssemblyTestbed


def test_queued_run_is_played_by_the_worker() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    started = testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
        )
    )

    assert started.status is AutotestRunStatus.RUNNING
    assert started.version_status is AssistantVersionStatus.TESTING
    assert testbed.conversation.inbound_messages == []
    assert testbed.version(business.id, version.id).autotest_run_id == started.id
    with pytest.raises(ConflictError, match="being tested"):
        testbed.run_autotests(business.id, version.id)

    tick = testbed.run_worker()
    repeated = testbed.run_worker()

    assert (tick.queued_runs, tick.failures) == (1, 0)
    assert repeated.queued_runs == 0
    stored = testbed.run_repo.get(business.id, started.id)
    assert stored is not None
    assert stored.status is AutotestRunStatus.FINISHED
    assert len(stored.results) == GEORGIAN_SCENARIO_COUNT
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )


class UnfinishableRun:
    """Finishing a run fails, as when the database is down at its end."""

    def run(self, input_data: AutotestRunCompletion) -> AutotestRunView:
        del input_data
        raise ExternalServiceError("database is down")


def test_a_run_the_worker_cannot_finish_does_not_leave_the_version_testing() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    full = testbed.run_autotests(business.id, version.id)
    assert full.version_status is AssistantVersionStatus.READY
    worker = BackgroundWorker(
        periodic_jobs=[],
        queued_job_operators={
            RUN_AUTOTESTS_JOB: PipelineOperator(
                OrchestratorPipeline(
                    RunQueuedAutotestsOrchestrator(
                        testbed.resume_autotest_run_use_case,
                        testbed.run_scenario_use_case,
                        UnfinishableRun(),
                        testbed.abandon_autotest_run_use_case,
                        testbed.record_autotest_progress_use_case,
                    )
                )
            )
        },
        job_repo=testbed.job_repo,
        wall_clock=testbed.wall_clock,
        error_reporter=testbed.worker_errors,
        poll_seconds=WorkerPollSeconds(5),
        storage_scope=StorageScopeContext(),
    )
    started = testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
            languages=[LanguageTag("en")],
        )
    )

    attempts: int = 0
    while attempts < 10 and testbed.pending_jobs():
        testbed.advance(3600)
        worker.run_once()
        attempts += 1

    assert attempts == 5  # retried with backoff, then given up
    stored = testbed.run_repo.get(business.id, started.id)
    assert stored is not None
    assert stored.status is AutotestRunStatus.ERRORED
    assert testbed.version(business.id, version.id).status is (
        AssistantVersionStatus.READY
    )
    rerun = testbed.run_autotests(business.id, version.id)
    assert rerun.status is AutotestRunStatus.FINISHED


class ProgressSnapshots:
    """Records what the cabinet would see after every played scenario."""

    def __init__(self, testbed: AssemblyTestbed) -> None:
        self._testbed: AssemblyTestbed = testbed
        self.snapshots: list[tuple[str, int, int]] = []

    def run(self, input_data: AutotestRunProgress) -> None:
        self._testbed.record_autotest_progress_use_case.run(input_data)
        view = self._testbed.get_autotest_run_use_case.run(
            AssistantVersionQuery(
                user_id=self._testbed.owner_id,
                business_id=input_data.business_id,
                version_id=self._version_id(input_data),
            )
        )
        self.snapshots.append(
            (view.status.value, len(view.results), int(view.scenario_count))
        )

    def _version_id(self, input_data: AutotestRunProgress) -> AssistantVersionId:
        stored = self._testbed.run_repo.get(input_data.business_id, input_data.run_id)
        assert stored is not None
        return stored.assistant_version_id


def test_a_running_run_shows_its_progress_scenario_by_scenario() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    progress = ProgressSnapshots(testbed)
    worker = BackgroundWorker(
        periodic_jobs=[],
        queued_job_operators={
            RUN_AUTOTESTS_JOB: PipelineOperator(
                OrchestratorPipeline(
                    RunQueuedAutotestsOrchestrator(
                        testbed.resume_autotest_run_use_case,
                        testbed.run_scenario_use_case,
                        testbed.finish_autotest_run_use_case,
                        testbed.abandon_autotest_run_use_case,
                        progress,
                    )
                )
            )
        },
        job_repo=testbed.job_repo,
        wall_clock=testbed.wall_clock,
        error_reporter=testbed.worker_errors,
        poll_seconds=WorkerPollSeconds(5),
        storage_scope=StorageScopeContext(),
    )
    started = testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
            languages=[LanguageTag("en")],
        )
    )
    planned = int(started.scenario_count)
    assert planned > 2
    assert started.results == []

    worker.run_once()

    assert progress.snapshots == [
        ("running", done, planned) for done in range(1, planned)
    ]
    finished = testbed.get_autotest_run_use_case.run(
        AssistantVersionQuery(
            user_id=testbed.owner_id, business_id=business.id, version_id=version.id
        )
    )
    assert finished.status is AutotestRunStatus.FINISHED
    assert len(finished.results) == planned == int(finished.scenario_count)


def test_progress_is_not_written_into_a_run_that_already_ended() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    finished = testbed.run_autotests(business.id, version.id)

    testbed.record_autotest_progress_use_case.run(
        AutotestRunProgress(business_id=business.id, run_id=finished.id, results=[])
    )

    stored = testbed.run_repo.get(business.id, finished.id)
    assert stored is not None
    assert len(stored.results) == int(finished.scenario_count) > 0

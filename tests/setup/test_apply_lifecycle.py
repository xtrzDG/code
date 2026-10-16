"""An apply under way, an apply that died, and checks that are not the apply's."""

from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.assistants.run_queued_autotests_orchestrator import (
    RunQueuedAutotestsOrchestrator,
)
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.setup import ApplyAttentionCode, ApplyChangesStage
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import AutotestRunCompletion
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed
from tests.setup.apply_testbed import (
    apply,
    assert_needs_attention,
    progress,
    settle,
    stored_apply,
)


class UnfinishableRun:
    """Finishing a run fails on every attempt, as when the database is down."""

    def run(self, input_data: AutotestRunCompletion) -> AutotestRunView:
        del input_data
        raise ExternalServiceError("database is down")


def test_checks_the_worker_gives_up_on_stop_the_apply() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    worker = testbed.background_worker(
        {
            RUN_AUTOTESTS_JOB: PipelineOperator(
                OrchestratorPipeline(
                    RunQueuedAutotestsOrchestrator(
                        testbed.resume_autotest_run_use_case,
                        testbed.run_scenario_use_case,
                        UnfinishableRun(),
                        testbed.abandon_autotest_run_use_case,
                        testbed.record_autotest_progress_use_case,
                        testbed.publish_applied_use_case,
                    )
                )
            )
        }
    )
    apply(testbed, business)

    attempts: int = 0
    while attempts < 10 and testbed.pending_jobs():
        testbed.advance(3600)
        worker.run_once()
        attempts += 1

    view = progress(testbed, business)
    assert_needs_attention(view, ApplyAttentionCode.CHECKS_STOPPED)
    assert testbed.business(business.id).published_assistant_version_id is None
    # Applying again starts new checks of the same, unchanged profile.
    again = apply(testbed, business)
    assert again.stage is ApplyChangesStage.CHECKING


def test_an_apply_under_way_is_returned_instead_of_a_new_one() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    first = apply(testbed, business)

    second = apply(testbed, business)

    assert second.stage is ApplyChangesStage.CHECKING
    assert second.assistant_version_id == first.assistant_version_id
    assert second.started_at == first.started_at
    assert len(testbed.version_repo.list_by_business(business.id)) == 1
    assert len(testbed.pending_jobs()) == 1
    created = [
        entry
        for entry in testbed.audit_repo.list_by_business(business.id)
        if str(entry.entity) == "assistant_apply"
    ]
    assert [entry.action for entry in created] == [AuditAction.CREATE]


def test_an_apply_whose_request_died_is_replaced_after_a_while() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    first = apply(testbed, business)
    # The request died while it was still building.
    stuck = stored_apply(testbed, business)
    stuck.stage = ApplyChangesStage.BUILDING
    stuck.assistant_version_id = None
    testbed.apply_repo.save(stuck)

    soon = apply(testbed, business)
    testbed.advance(16 * 60)
    later = apply(testbed, business)

    assert soon.stage is ApplyChangesStage.BUILDING
    assert soon.started_at == first.started_at
    assert later.stage is ApplyChangesStage.CHECKING
    assert later.started_at != first.started_at
    assert later.version_number == 2


def test_checks_of_another_version_do_not_publish_or_move_the_apply() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    started = apply(testbed, business)
    # A version checked from Advanced while the apply waits for its own.
    other = testbed.assemble(business.id, run_autotests=True)
    assert other.status is AssistantVersionStatus.READY

    testbed.publish_applied_use_case.run(
        AppliedVersion(business_id=business.id, assistant_version_id=other.id)
    )

    view = progress(testbed, business)
    assert view.stage is ApplyChangesStage.CHECKING
    assert view.assistant_version_id == started.assistant_version_id
    assert testbed.business(business.id).published_assistant_version_id is None


def test_a_checked_version_with_nothing_changed_is_published_at_once() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    checked = testbed.assemble(business.id, run_autotests=True)
    assert checked.status is AssistantVersionStatus.READY

    view = apply(testbed, business)

    assert view.stage is ApplyChangesStage.LIVE
    assert view.assistant_version_id == checked.id
    assert testbed.pending_jobs() == []
    assert testbed.business(business.id).published_assistant_version_id == checked.id
    assert testbed.version(business.id, checked.id).status is (
        AssistantVersionStatus.PUBLISHED
    )
    published = [
        entry
        for entry in testbed.audit_repo.list_by_business(business.id)
        if str(entry.entity) == "assistant_version"
        and entry.action is AuditAction.UPDATE
    ]
    assert [str(entry.actor_id) for entry in published] == [str(testbed.owner_id)]


def test_while_checking_the_progress_counts_the_checks_played() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))

    started = apply(testbed, business)

    assert started.checks_done == 0
    assert started.checks_total is not None
    assert int(started.checks_total) > 0
    assert started.is_in_progress is True
    assert started.has_unapplied_changes is True

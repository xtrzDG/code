"""
Giving up an autotest run that will not be played to its end: the run is
ERRORED ("could not be completed") and a version still TESTING because of
it gets back the status it had before, so the owner can run the autotests
again instead of waiting forever.
"""

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument


def give_up_run(
    assistant_version_repo: AssistantVersionRepoContract,
    autotest_run_repo: AutotestRunRepoContract,
    live_events: EventPublisherFacilitatorContract,
    run: AutotestRunDocument,
    now: Microseconds,
) -> None:
    """The RUNNING `run` ERRORED, its version restored, open cabinets told."""

    run.status = AutotestRunStatus.ERRORED
    run.updated_at = now
    autotest_run_repo.save(run)
    version: AssistantVersionDocument | None = assistant_version_repo.get(
        run.business_id,
        run.assistant_version_id,
    )
    if (
        version is not None
        and version.status is AssistantVersionStatus.TESTING
        and version.autotest_run_id == run.id
    ):
        version.status = run.previous_version_status or AssistantVersionStatus.DRAFT
        version.updated_at = now
        assistant_version_repo.save(version)
    live_events.publish(
        run.business_id,
        LiveEventKind.AUTOTEST_PROGRESS,
        (run.id, run.assistant_version_id),
    )

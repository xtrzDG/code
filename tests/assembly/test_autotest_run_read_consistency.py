"""
A finished autotest run is never shown with its version still testing.

The worker finishes a run in a lane thread while the cabinet polls it: the
version's final status is saved before the run turns FINISHED, and the read
takes the version again once it sees the run finished.
"""

import pytest

from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.dto.assistants.assistant_commands import AssistantVersionQuery
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.assembly.autotest_run_helpers import start
from tests.assembly.testbed import AssemblyTestbed


def test_the_version_is_saved_before_its_run_turns_finished(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    saves: list[str] = []
    save_version = testbed.version_repo.save
    save_run = testbed.run_repo.save

    def record_version(document: AssistantVersionDocument) -> None:
        saves.append(f"version:{document.status.value}")
        save_version(document)

    def record_run(document: AutotestRunDocument) -> None:
        saves.append(f"run:{document.status.value}")
        save_run(document)

    monkeypatch.setattr(testbed.version_repo, "save", record_version)
    monkeypatch.setattr(testbed.run_repo, "save", record_run)

    testbed.run_autotests(business.id, version.id)

    finished_at: int = saves.index(f"run:{AutotestRunStatus.FINISHED.value}")
    assert f"version:{AssistantVersionStatus.READY.value}" in saves[:finished_at]


def test_a_run_that_finishes_between_the_two_reads_shows_the_final_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.run_autotests(business.id, version.id)
    read_version = testbed.version_repo.get
    reads: list[AssistantVersionId] = []

    def read_before_the_worker_saved_it(
        business_id: BusinessId,
        version_id: AssistantVersionId,
    ) -> AssistantVersionDocument | None:
        stored = read_version(business_id, version_id)
        reads.append(version_id)
        if stored is None or len(reads) > 1:
            return stored

        return stored.model_copy(update={"status": AssistantVersionStatus.TESTING})

    monkeypatch.setattr(testbed.version_repo, "get", read_before_the_worker_saved_it)

    shown = testbed.get_autotest_run_use_case.run(
        AssistantVersionQuery(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
        )
    )

    assert shown.status is AutotestRunStatus.FINISHED
    assert shown.version_status is AssistantVersionStatus.READY

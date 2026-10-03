"""Re-encryption runs: one at a time, stale ones replaced, failures kept."""

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.key_rotation_repository import KeyRotationRepository
from app.schemas.constants.security import KeyRotationStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.key_rotation import KeyRotationJobPayload
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.security.constrained_integers import EncryptionKeyCount
from app.schemas.typings.security.prefixed_id import KeyRotationId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.security.rotate_encrypted_secrets_use_case import (
    RotateEncryptedSecretsUseCase,
)
from app.use_cases.admin.security.secret_resealer import RotationTally
from tests.storage.storage_testing import build_fixed_wall_clock

HOUR: int = 3600 * 1_000_000


def run(
    at: int, status: KeyRotationStatus = KeyRotationStatus.QUEUED
) -> KeyRotationDocument:
    return KeyRotationDocument(
        status=status,
        requested_by=UserId(),
        key_count=EncryptionKeyCount(2),
        created_at=Microseconds(at),
        updated_at=Microseconds(at),
    )


def repository() -> KeyRotationRepository:
    return KeyRotationRepository(
        InMemoryDocumentCollectionAdapter[KeyRotationDocument](KeyRotationDocument)
    )


def test_only_one_run_at_a_time_unless_it_went_stale() -> None:
    repo = repository()
    first = run(10 * HOUR)

    assert repo.start(first, Microseconds(9 * HOUR))
    assert not repo.start(run(10 * HOUR + 1), Microseconds(9 * HOUR))
    assert repo.start(run(12 * HOUR), Microseconds(11 * HOUR))  # first is stale
    latest = repo.get_latest()
    assert latest is not None and latest.id != first.id


def test_a_finished_run_makes_room_and_old_runs_are_not_updated() -> None:
    repo = repository()
    finished = run(HOUR, KeyRotationStatus.DONE)
    assert repo.start(finished, Microseconds(0))
    newer = run(HOUR + 1)

    assert repo.start(newer, Microseconds(0))
    assert repo.update(finished.id, lambda stored: stored) is None
    assert repo.update(KeyRotationId(), lambda stored: stored) is None


class FailingBusinessRepo:
    def list_all(self) -> list[BusinessDocument]:
        raise RuntimeError("database went away")


class CountingResealer:
    def reseal_business(self, business_id: object, tally: RotationTally) -> None:
        del business_id
        tally.total += 1


class OneKeyRotation:
    def key_count(self) -> EncryptionKeyCount:
        return EncryptionKeyCount(1)


def job_for(rotation_id: KeyRotationId) -> QueuedJobInput:
    return QueuedJobInput(
        job_id=QueuedJobId(),
        job_name=JobName("rotate_encrypted_secrets"),
        payload=JobPayloadJson(
            KeyRotationJobPayload(rotation_id=rotation_id).model_dump_json()
        ),
    )


def use_case(
    repo: KeyRotationRepository, businesses: object
) -> RotateEncryptedSecretsUseCase:
    return RotateEncryptedSecretsUseCase(
        business_repo=businesses,  # type: ignore[arg-type]
        key_rotation_repo=repo,
        secret_rotation=OneKeyRotation(),  # type: ignore[arg-type]
        resealer=CountingResealer(),  # type: ignore[arg-type]
        wall_clock=build_fixed_wall_clock(),
    )


def test_a_failed_run_keeps_its_error_and_the_job_retries() -> None:
    repo = repository()
    rotation = run(0)
    repo.start(rotation, Microseconds(0))

    with pytest.raises(RuntimeError, match="database went away"):
        use_case(repo, FailingBusinessRepo()).run(job_for(rotation.id))

    failed = repo.get_latest()
    assert failed is not None
    assert failed.status is KeyRotationStatus.FAILED
    assert str(failed.last_error) == "RuntimeError: database went away"
    assert failed.started_at is not None and failed.finished_at is not None


def test_a_replaced_run_is_skipped() -> None:
    repo = repository()
    repo.start(run(0, KeyRotationStatus.DONE), Microseconds(0))

    report = use_case(repo, FailingBusinessRepo()).run(job_for(KeyRotationId()))

    assert int(report.processed_count) == 0

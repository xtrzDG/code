from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.key_rotations import KeyRotationRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.secret_cipher import SecretRotationAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.key_rotation import (
    KeyRotationJobPayload,
    KeyRotationStarted,
    StartKeyRotationCommand,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.security.key_rotation_views import (
    ROTATE_ENCRYPTED_SECRETS_JOB,
    ROTATION_SERIAL_KEY,
    build_key_rotation_view,
    build_rotation_audit_entry,
)

# A run that has not moved for this long died with its worker.
STALE_ROTATION_MICROSECONDS: int = 60 * 60 * 1_000_000


class StartKeyRotationUseCase(
    UseCaseContract[StartKeyRotationCommand, KeyRotationStarted]
):
    """
    A platform admin has every stored secret sealed again with the current
    key of the ring (after a new key was put first in ENCRYPTION_KEYS):
    the run is recorded as QUEUED, the `rotate_encrypted_secrets` job is
    queued and the request is audited. One run at a time.

    Raises:
        AccessDeniedError: the user is not a platform admin.
        ConflictError: a run is queued or running.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[UserId, UserDocument],
        secret_rotation: SecretRotationAdapterContract,
        key_rotation_repo: KeyRotationRepoContract,
        job_queue: JobQueueFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[UserId, UserDocument] = (
            authorize_platform_admin
        )
        self._secret_rotation: SecretRotationAdapterContract = secret_rotation
        self._key_rotation_repo: KeyRotationRepoContract = key_rotation_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StartKeyRotationCommand) -> KeyRotationStarted:
        admin: UserDocument = self._authorize_platform_admin.run(input_data.user_id)
        now: Microseconds = self._wall_clock.now_unix()
        rotation = KeyRotationDocument(
            requested_by=admin.id,
            key_count=self._secret_rotation.key_count(),
            created_at=now,
            updated_at=now,
        )
        stale_before = Microseconds(int(now) - STALE_ROTATION_MICROSECONDS)
        if not self._key_rotation_repo.start(rotation, stale_before):
            raise ConflictError(
                "A re-encryption of the stored secrets is already running."
            )

        self._job_queue.enqueue(
            ROTATE_ENCRYPTED_SECRETS_JOB,
            JobPayloadJson(
                KeyRotationJobPayload(rotation_id=rotation.id).model_dump_json()
            ),
            None,
            lane=JobLane.DEFAULT,
            serial_key=ROTATION_SERIAL_KEY,
        )
        entry: AuditLogEntryDocument = build_rotation_audit_entry(
            admin.id, rotation, input_data.client_ip_address, now
        )
        self._audit_log_repo.append(entry)
        return KeyRotationStarted(
            rotation=build_key_rotation_view(rotation),
            audit_log_entry_id=entry.id,
        )

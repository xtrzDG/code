import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.key_rotations import KeyRotationRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.secret_cipher import SecretRotationAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.security import KeyRotationStatus
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.key_rotation import KeyRotationJobPayload
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.strings import JobErrorText
from app.schemas.typings.security.constrained_integers import (
    StoredSecretCount,
    WebhookRegistrationCount,
)
from app.use_cases.admin.security.secret_resealer import RotationTally, SecretResealer

LOGGER: logging.Logger = logging.getLogger(__name__)
MAX_ERROR_LENGTH: int = 500


class RotateEncryptedSecretsUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    The `rotate_encrypted_secrets` job: walk every business and seal each
    stored secret (channel credentials, Google Calendar tokens) with the
    current key of the ring, then register Telegram webhooks again with the
    current key's secret when the ring holds older keys. The run's record
    shows the counts; a previous key may be dropped once a run ends DONE
    with nothing unreadable and no failed webhook.

    Idempotent: a retried or repeated run finds the moved secrets current.
    A failure marks the run FAILED (with the error) and lets the job retry.
    Runs platform-wide (it reads every business).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        key_rotation_repo: KeyRotationRepoContract,
        secret_rotation: SecretRotationAdapterContract,
        resealer: SecretResealer,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._key_rotation_repo: KeyRotationRepoContract = key_rotation_repo
        self._secret_rotation: SecretRotationAdapterContract = secret_rotation
        self._resealer: SecretResealer = resealer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        payload = KeyRotationJobPayload.model_validate_json(str(input_data.payload))
        started_at: Microseconds = self._wall_clock.now_unix()
        started = self._key_rotation_repo.update(
            payload.rotation_id,
            lambda rotation: rotation.model_copy(
                update={
                    "status": KeyRotationStatus.RUNNING,
                    "key_count": self._secret_rotation.key_count(),
                    "started_at": started_at,
                    "last_error": None,
                    "updated_at": started_at,
                }
            ),
        )
        if started is None:
            LOGGER.info("Key rotation %s was replaced; skipped", payload.rotation_id)
            return JobReport()

        tally = RotationTally()
        try:
            for business in self._business_repo.list_all():
                self._resealer.reseal_business(business.id, tally)
        except Exception as error:
            self._finish(started, tally, KeyRotationStatus.FAILED, error)
            raise

        self._finish(started, tally, KeyRotationStatus.DONE, None)
        LOGGER.info(
            "Key rotation %s: %d secrets, %d rotated, %d current, %d unreadable; "
            "%d webhooks renewed, %d failed",
            started.id,
            tally.total,
            tally.rotated,
            tally.current,
            tally.unreadable,
            tally.webhooks_renewed,
            tally.webhooks_failed,
        )
        return JobReport(processed_count=ProcessedItemCount(tally.total))

    def _finish(
        self,
        rotation: KeyRotationDocument,
        tally: RotationTally,
        status: KeyRotationStatus,
        error: Exception | None,
    ) -> None:
        finished_at: Microseconds = self._wall_clock.now_unix()
        self._key_rotation_repo.update(
            rotation.id,
            lambda stored: stored.model_copy(
                update={
                    "status": status,
                    "secrets_total": StoredSecretCount(tally.total),
                    "secrets_current": StoredSecretCount(tally.current),
                    "secrets_rotated": StoredSecretCount(tally.rotated),
                    "secrets_unreadable": StoredSecretCount(tally.unreadable),
                    "webhooks_renewed": WebhookRegistrationCount(
                        tally.webhooks_renewed
                    ),
                    "webhooks_failed": WebhookRegistrationCount(tally.webhooks_failed),
                    "finished_at": finished_at,
                    "last_error": None
                    if error is None
                    else JobErrorText(
                        f"{type(error).__name__}: {error}"[:MAX_ERROR_LENGTH]
                    ),
                    "updated_at": finished_at,
                }
            ),
        )

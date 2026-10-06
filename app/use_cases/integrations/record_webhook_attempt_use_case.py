import logging
import random
from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
    WebhookEndpointRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import (
    WebhookDeliveryProblem,
    WebhookDeliveryStatus,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.dto.integrations.webhook_attempts import WebhookAttempt
from app.schemas.typings.integrations.constrained_integers import (
    WebhookAttemptCount,
    WebhookFailuresBeforeDisable,
)
from app.use_cases.integrations.endpoint_health import record_endpoint_outcome
from app.use_cases.shared.storage_transaction import in_unit_of_work
from app.utilities.integrations.webhook_jobs import (
    DELIVER_WEBHOOK_JOB,
    encode_webhook_job,
)
from app.utilities.integrations.webhook_schedule import (
    MICROSECONDS_PER_SECOND,
    retry_delay_seconds,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
# Attempts a retry cannot help: the address is refused by the SSRF guard,
# the receiver said Gone, the endpoint is off.
FINAL_PROBLEMS: frozenset[WebhookDeliveryProblem] = frozenset(
    {
        WebhookDeliveryProblem.NOT_PUBLIC,
        WebhookDeliveryProblem.GONE,
        WebhookDeliveryProblem.ENDPOINT_OFF,
    }
)


class RecordWebhookAttemptUseCase(
    UseCaseContract[WebhookAttempt, WebhookDeliveryDocument | None]
):
    """
    Store what an attempt did. A 2xx answer: DELIVERED. A failure that a
    retry may fix, inside the delivery's 24 hours: PENDING again with the
    next attempt on the schedule (30 s, 2 min, 10 min ... 8 h, with jitter)
    and its job queued in the same transaction. Otherwise (the last chance
    passed, the address refused, 410 Gone, the endpoint off, a test event):
    FAILED. Written only while the delivery still waits, so two workers
    never both record one attempt. The endpoint follows
    (`record_endpoint_outcome`): a success resets its failures, a failure
    counts, and past WEBHOOK_DISABLE_AFTER_FAILURES in a row, or on 410
    Gone, it is switched off.
    """

    def __init__(
        self,
        delivery_repo: WebhookDeliveryRepoContract,
        endpoint_repo: WebhookEndpointRepoContract,
        job_queue: JobQueueFacilitatorContract,
        unit_of_work: StorageUnitOfWorkContract | None,
        failures_before_disable: WebhookFailuresBeforeDisable,
        # Spreads retry times only; nothing secret depends on it.
        jitter: Callable[[], float] = random.random,  # nosec B311
    ) -> None:
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo
        self._endpoint_repo: WebhookEndpointRepoContract = endpoint_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work
        self._failures_before_disable: WebhookFailuresBeforeDisable = (
            failures_before_disable
        )
        self._jitter: Callable[[], float] = jitter

    def run(self, input_data: WebhookAttempt) -> WebhookDeliveryDocument | None:
        delivery = input_data.delivery
        now: Microseconds = input_data.attempted_at
        attempts = WebhookAttemptCount(int(delivery.attempts) + 1)
        next_attempt_at: Microseconds | None = self._next_attempt(input_data, attempts)

        def record(current: WebhookDeliveryDocument) -> WebhookDeliveryDocument | None:
            if current.status is not WebhookDeliveryStatus.PENDING:
                return None

            result = input_data.result
            delivered: bool = result.problem is None
            return current.model_copy(
                update={
                    "attempts": attempts,
                    "last_attempt_at": now,
                    "last_status_code": result.status_code,
                    "last_problem": result.problem,
                    "last_error": result.error,
                    "next_attempt_at": next_attempt_at,
                    "delivered_at": now if delivered else current.delivered_at,
                    "status": WebhookDeliveryStatus.DELIVERED
                    if delivered
                    else WebhookDeliveryStatus.PENDING
                    if next_attempt_at is not None
                    else WebhookDeliveryStatus.FAILED,
                    "updated_at": now,
                }
            )

        with in_unit_of_work(self._unit_of_work):
            stored = self._delivery_repo.update(
                delivery.business_id, delivery.id, record
            )
            if stored is None:
                return None

            if next_attempt_at is not None:
                self._job_queue.enqueue(
                    DELIVER_WEBHOOK_JOB,
                    encode_webhook_job(stored.business_id, stored.id),
                    stored.business_id,
                    run_at=next_attempt_at,
                    lane=JobLane.DEFAULT,
                )
            record_endpoint_outcome(
                self._endpoint_repo, stored, input_data, self._failures_before_disable
            )
        if stored.status is WebhookDeliveryStatus.FAILED:
            LOGGER.warning(
                "Webhook delivery %s (%s) given up after %d attempt(s): %s",
                stored.id,
                stored.event_type.value,
                int(stored.attempts),
                None if stored.last_problem is None else stored.last_problem.value,
            )
        return stored

    def _next_attempt(
        self, attempt: WebhookAttempt, attempts: WebhookAttemptCount
    ) -> Microseconds | None:
        """When to try again, or None: delivered, or no retry may help."""

        problem = attempt.result.problem
        if problem is None or problem in FINAL_PROBLEMS or attempt.delivery.is_test:
            return None

        delay: int = retry_delay_seconds(int(attempts), self._jitter())
        moment = int(attempt.attempted_at) + delay * MICROSECONDS_PER_SECOND
        if moment > int(attempt.delivery.give_up_at):
            return None

        return Microseconds(moment)

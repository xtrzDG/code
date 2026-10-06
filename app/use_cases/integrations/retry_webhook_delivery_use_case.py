from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import WebhookDeliveryStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.webhook_views import (
    WebhookDeliveryCommand,
    WebhookDeliveryView,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.use_cases.integrations.webhook_records import delivery_view
from app.use_cases.shared.storage_transaction import in_unit_of_work
from app.utilities.integrations.webhook_jobs import (
    DELIVER_WEBHOOK_JOB,
    encode_webhook_job,
)
from app.utilities.integrations.webhook_schedule import give_up_moment


class RetryWebhookDeliveryUseCase(
    UseCaseContract[WebhookDeliveryCommand, WebhookDeliveryView]
):
    """
    The owner sends a delivery again from the log (after fixing the
    receiver): the same event and body, signed anew, tried at once and
    then on the usual schedule for another 24 hours. A test event is sent
    with "Send test event" instead. Owners only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        delivery_repo: WebhookDeliveryRepoContract,
        job_queue: JobQueueFacilitatorContract,
        unit_of_work: StorageUnitOfWorkContract | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._delivery_repo: WebhookDeliveryRepoContract = delivery_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WebhookDeliveryCommand) -> WebhookDeliveryView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        delivery = self._delivery_repo.get(business.id, input_data.delivery_id)
        if delivery is None:
            raise NotFoundError("This delivery does not exist (any more).")

        if delivery.is_test:
            raise ConflictError("A test event is sent again with Send test event.")

        now: Microseconds = self._wall_clock.now_unix()

        def requeue(current: WebhookDeliveryDocument) -> WebhookDeliveryDocument:
            return current.model_copy(
                update={
                    "status": WebhookDeliveryStatus.PENDING,
                    "next_attempt_at": now,
                    "give_up_at": Microseconds(give_up_moment(int(now))),
                    "updated_at": now,
                }
            )

        with in_unit_of_work(self._unit_of_work):
            stored = self._delivery_repo.update(business.id, delivery.id, requeue)
            if stored is None:
                raise NotFoundError("This delivery does not exist (any more).")

            self._job_queue.enqueue(
                DELIVER_WEBHOOK_JOB,
                encode_webhook_job(business.id, stored.id),
                business.id,
                lane=JobLane.DEFAULT,
            )
        return delivery_view(stored)

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.service_metrics import ServiceMetricsContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.constants.telemetry import WebhookMessageOutcome
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from app.schemas.dto.deliveries import InboxIntake, RoutedInboundMessage
from app.schemas.typings.channels.constrained_integers import WebhookMessageCount
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.use_cases.shared.inbox_queue import store_and_queue
from app.utilities.channels.channel_activity import stamp_channel_activity_by_id
from app.utilities.deliveries.delivery_jobs import PROCESS_INBOUND_MESSAGE_JOB
from app.utilities.deliveries.delivery_keys import (
    bounded_provider_message_id,
    derive_inbound_event_id,
    inbound_serial_key,
)
from app.utilities.deliveries.inbox_messages import build_inbound_customer_message
from app.utilities.observability.metrics.null_service_metrics import (
    NO_SERVICE_METRICS,
)

ONE_MESSAGE: WebhookMessageCount = WebhookMessageCount(1)


class StoreInboundMessagesUseCase(
    UseCaseContract[list[RoutedInboundMessage], InboxIntake]
):
    """
    Put the verified customer messages of one webhook into the inbox and
    queue `process_inbound_message` for each new one (inbound lane, one
    customer's messages one at a time, oldest first).

    A message the platform delivered before is the same event (its id is
    derived from the business, channel and platform message id) and is not
    queued again, so a redelivered webhook gets no second answer. Nothing
    slow happens here: the worker answers. A channel that brought a new
    message notes when (`last_inbound_at`, to the minute), for its health
    line in the cabinet. Each message is counted for /metrics by channel:
    received, then queued or duplicate.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        channel_repo: ChannelRepoContract,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
        metrics: ServiceMetricsContract = NO_SERVICE_METRICS,
    ) -> None:
        self._metrics: ServiceMetricsContract = metrics
        self._channel_repo: ChannelRepoContract = channel_repo
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def run(self, input_data: list[RoutedInboundMessage]) -> InboxIntake:
        now: Microseconds = self._wall_clock.now_unix()
        queued: int = 0
        active_channels: list[ChannelId] = []
        for routed in input_data:
            event: InboundEventDocument = build_customer_event(routed, now)
            self._metrics.count_webhook_messages(
                routed.channel, WebhookMessageOutcome.RECEIVED, ONE_MESSAGE
            )
            is_new: bool = store_and_queue(
                self._inbound_event_repo,
                self._job_queue,
                event,
                PROCESS_INBOUND_MESSAGE_JOB,
                inbound_serial_key(
                    routed.business_id,
                    routed.channel,
                    str(routed.message.channel_user_id),
                ),
                unit_of_work=self._unit_of_work,
            )
            self._metrics.count_webhook_messages(
                routed.channel,
                WebhookMessageOutcome.QUEUED
                if is_new
                else WebhookMessageOutcome.DUPLICATE,
                ONE_MESSAGE,
            )
            if is_new:
                queued += 1
                if routed.channel_id not in active_channels:
                    active_channels.append(routed.channel_id)

        for channel_id in active_channels:
            stamp_channel_activity_by_id(
                self._channel_repo, channel_id, MessageDirection.INBOUND, now
            )

        return InboxIntake(
            received=WebhookMessageCount(len(input_data)),
            queued=WebhookMessageCount(queued),
            duplicates=WebhookMessageCount(len(input_data) - queued),
        )


def build_customer_event(
    routed: RoutedInboundMessage,
    now: Microseconds,
) -> InboundEventDocument:
    message: ChannelInboundMessage = routed.message
    provider_message_id: ProviderMessageId = bounded_provider_message_id(
        message.provider_message_id
    )
    return InboundEventDocument(
        id=derive_inbound_event_id(
            routed.business_id, routed.channel, provider_message_id
        ),
        business_id=routed.business_id,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=routed.channel,
        channel_id=routed.channel_id,
        provider_message_id=provider_message_id,
        customer_message=build_inbound_customer_message(
            message.channel_user_id,
            message.text,
            message.contact_name,
            message.contact_phone_number,
            message.attachments,
            message.acquisition_source,
        ),
        created_at=now,
        updated_at=now,
    )

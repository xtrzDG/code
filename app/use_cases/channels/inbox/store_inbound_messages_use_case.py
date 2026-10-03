from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from app.schemas.dto.deliveries import InboxIntake, RoutedInboundMessage
from app.schemas.typings.channels.constrained_integers import WebhookMessageCount
from app.schemas.typings.channels.strings import ProviderMessageId
from app.use_cases.shared.inbox_queue import store_and_queue
from app.utilities.deliveries.delivery_jobs import PROCESS_INBOUND_MESSAGE_JOB
from app.utilities.deliveries.delivery_keys import (
    bounded_provider_message_id,
    derive_inbound_event_id,
    inbound_serial_key,
)
from app.utilities.deliveries.inbox_messages import build_inbound_customer_message


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
    slow happens here: the worker answers.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: list[RoutedInboundMessage]) -> InboxIntake:
        now: Microseconds = self._wall_clock.now_unix()
        queued: int = 0
        for routed in input_data:
            event: InboundEventDocument = build_customer_event(routed, now)
            if store_and_queue(
                self._inbound_event_repo,
                self._job_queue,
                event,
                PROCESS_INBOUND_MESSAGE_JOB,
                inbound_serial_key(
                    routed.business_id,
                    routed.channel,
                    str(routed.message.channel_user_id),
                ),
            ):
                queued += 1

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
        ),
        created_at=now,
        updated_at=now,
    )

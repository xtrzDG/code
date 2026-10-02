from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.channel_webhooks import ChannelWebhookOutcome
from app.schemas.dto.deliveries import InboxIntake, RoutedInboundMessage


class ChannelWebhookOrchestrator[WebhookRequest](
    OrchestratorContract[WebhookRequest, ChannelWebhookOutcome]
):
    """
    One webhook delivery of a messaging channel (concept section 1, path of
    a message), acknowledged in milliseconds: verify and read it, store
    every customer message in the inbox and queue it for the background
    worker, which answers and sends the reply through the outbox.

    Nothing slow happens in the request, so the platform never times out
    and redelivers; a redelivered message is recognised in the inbox and
    not answered twice. A request that fails before its messages are stored
    is refused, so the platform delivers it again.
    """

    def __init__(
        self,
        receive_webhook: UseCaseContract[WebhookRequest, list[RoutedInboundMessage]],
        store_inbound_messages: UseCaseContract[
            list[RoutedInboundMessage], InboxIntake
        ],
    ) -> None:
        self._receive_webhook: UseCaseContract[
            WebhookRequest,
            list[RoutedInboundMessage],
        ] = receive_webhook
        self._store_inbound_messages: UseCaseContract[
            list[RoutedInboundMessage], InboxIntake
        ] = store_inbound_messages

    def execute(self, input_data: WebhookRequest) -> ChannelWebhookOutcome:
        routed: list[RoutedInboundMessage] = self._receive_webhook.run(input_data)
        intake: InboxIntake = self._store_inbound_messages.run(routed)
        return ChannelWebhookOutcome(
            received=intake.received,
            queued=intake.queued,
            duplicates=intake.duplicates,
        )

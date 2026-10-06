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
    is refused, so the platform delivers it again. Where the platform waits
    for it, a stored delivery is then acknowledged (a Telegram button tap is
    answered: two short platform calls, best effort).
    """

    def __init__(
        self,
        receive_webhook: UseCaseContract[WebhookRequest, list[RoutedInboundMessage]],
        store_inbound_messages: UseCaseContract[
            list[RoutedInboundMessage], InboxIntake
        ],
        acknowledge_webhook: UseCaseContract[WebhookRequest, None] | None = None,
    ) -> None:
        self._receive_webhook: UseCaseContract[
            WebhookRequest,
            list[RoutedInboundMessage],
        ] = receive_webhook
        self._store_inbound_messages: UseCaseContract[
            list[RoutedInboundMessage], InboxIntake
        ] = store_inbound_messages
        self._acknowledge_webhook: UseCaseContract[WebhookRequest, None] | None = (
            acknowledge_webhook
        )

    def execute(self, input_data: WebhookRequest) -> ChannelWebhookOutcome:
        routed: list[RoutedInboundMessage] = self._receive_webhook.run(input_data)
        intake: InboxIntake = self._store_inbound_messages.run(routed)
        if self._acknowledge_webhook is not None and routed:
            self._acknowledge_webhook.run(input_data)

        return ChannelWebhookOutcome(
            received=intake.received,
            queued=intake.queued,
            duplicates=intake.duplicates,
        )

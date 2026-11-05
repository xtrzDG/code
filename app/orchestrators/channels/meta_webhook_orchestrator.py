from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.channel_webhooks import (
    ChannelWebhookOutcome,
    MetaWebhookRequest,
)
from app.schemas.dto.deliveries import InboxIntake, RoutedInboundMessage
from app.schemas.typings.channels.constrained_integers import WebhookMessageCount


class MetaWebhookOrchestrator(
    OrchestratorContract[MetaWebhookRequest, ChannelWebhookOutcome]
):
    """
    One delivery of the platform's Meta webhook (WhatsApp, Messenger and
    Instagram), acknowledged in milliseconds like every channel's
    (`ChannelWebhookOrchestrator`): verify and read the messages, store them
    in the inbox and queue them for the worker; then the Instagram comments
    that ask for a private reply, stored and queued the same way.

    A delivery whose signature is wrong is refused before anything is
    stored, so Meta never has a forged one answered; one that fails before
    its events are stored is refused too, and Meta delivers it again (the
    inbox recognises what it stored before).
    """

    def __init__(
        self,
        receive_webhook: UseCaseContract[
            MetaWebhookRequest, list[RoutedInboundMessage]
        ],
        store_inbound_messages: UseCaseContract[
            list[RoutedInboundMessage], InboxIntake
        ],
        accept_comments: UseCaseContract[MetaWebhookRequest, InboxIntake],
    ) -> None:
        self._receive_webhook: UseCaseContract[
            MetaWebhookRequest, list[RoutedInboundMessage]
        ] = receive_webhook
        self._store_inbound_messages: UseCaseContract[
            list[RoutedInboundMessage], InboxIntake
        ] = store_inbound_messages
        self._accept_comments: UseCaseContract[MetaWebhookRequest, InboxIntake] = (
            accept_comments
        )

    def execute(self, input_data: MetaWebhookRequest) -> ChannelWebhookOutcome:
        routed: list[RoutedInboundMessage] = self._receive_webhook.run(input_data)
        messages: InboxIntake = self._store_inbound_messages.run(routed)
        comments: InboxIntake = self._accept_comments.run(input_data)
        return ChannelWebhookOutcome(
            received=WebhookMessageCount(
                int(messages.received) + int(comments.received)
            ),
            queued=WebhookMessageCount(int(messages.queued) + int(comments.queued)),
            duplicates=WebhookMessageCount(
                int(messages.duplicates) + int(comments.duplicates)
            ),
        )

import logging

from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels import (
    ChannelInboundDelivery,
    ChannelReplyDelivery,
    ChannelWebhookOutcome,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.constrained_integers import (
    DeliveredMessageCount,
    WebhookMessageCount,
)

logger: logging.Logger = logging.getLogger(__name__)


class ChannelWebhookOrchestrator[WebhookRequest](
    OrchestratorContract[WebhookRequest, ChannelWebhookOutcome]
):
    """
    One webhook delivery of a messaging channel (concept section 1, path of
    a message): verify and read it, let the assistant answer every customer
    message through the customer-message pipeline, send each answer back
    through the same channel. While staff handle a conversation the
    assistant stays silent and nothing is sent.

    A message that cannot be answered or delivered is logged and counted;
    the delivery is still acknowledged, so the platform does not repeat the
    messages that were answered. An unexpected error of one message is
    reported (logged with its trace, which the error reporter picks up) and
    never stops the other messages of the same delivery: their receipts are
    already recorded, so a failed request would lose them for good.
    """

    def __init__(
        self,
        receive_webhook: UseCaseContract[WebhookRequest, list[ChannelInboundDelivery]],
        customer_message_pipeline: CustomerMessagePipelineContract,
        deliver_reply: UseCaseContract[ChannelReplyDelivery, DeliveredMessageCount],
    ) -> None:
        self._receive_webhook: UseCaseContract[
            WebhookRequest,
            list[ChannelInboundDelivery],
        ] = receive_webhook
        self._customer_message_pipeline: CustomerMessagePipelineContract = (
            customer_message_pipeline
        )
        self._deliver_reply: UseCaseContract[
            ChannelReplyDelivery,
            DeliveredMessageCount,
        ] = deliver_reply

    def execute(self, input_data: WebhookRequest) -> ChannelWebhookOutcome:
        deliveries: list[ChannelInboundDelivery] = self._receive_webhook.run(input_data)
        answered: int = 0
        silenced: int = 0
        failed: int = 0
        for delivery in deliveries:
            try:
                reply: AssistantReply = self._customer_message_pipeline.start(
                    delivery.message
                )
            except ApplicationError as error:
                logger.warning(
                    "A %s message of business %s was not answered: %s",
                    delivery.message.channel.value,
                    delivery.message.business_id,
                    error,
                )
                failed += 1
                continue
            except Exception:
                logger.exception(
                    "A %s message of business %s failed unexpectedly.",
                    delivery.message.channel.value,
                    delivery.message.business_id,
                )
                failed += 1
                continue

            if reply.text is None:
                silenced += 1
                continue

            try:
                self._deliver_reply.run(
                    ChannelReplyDelivery(
                        business_id=delivery.message.business_id,
                        conversation_id=reply.conversation_id,
                        target=delivery.target,
                        text=reply.text,
                    )
                )
            except ApplicationError as error:
                logger.warning(
                    "A %s reply of business %s was not delivered: %s",
                    delivery.target.channel.value,
                    delivery.message.business_id,
                    error,
                )
                failed += 1
                continue
            except Exception:
                logger.exception(
                    "A %s reply of business %s failed unexpectedly.",
                    delivery.target.channel.value,
                    delivery.message.business_id,
                )
                failed += 1
                continue

            answered += 1

        return ChannelWebhookOutcome(
            received=WebhookMessageCount(len(deliveries)),
            answered=WebhookMessageCount(answered),
            silenced=WebhookMessageCount(silenced),
            failed=WebhookMessageCount(failed),
        )

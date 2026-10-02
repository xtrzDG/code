"""One bad message of a webhook delivery never loses the others."""

from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.channel_webhook_orchestrator import (
    ChannelWebhookOrchestrator,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelInboundDelivery,
    ChannelReplyDelivery,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag

BUSINESS_ID: BusinessId = BusinessId()


def delivery(text: str) -> ChannelInboundDelivery:
    return ChannelInboundDelivery(
        message=InboundMessage(
            business_id=BUSINESS_ID,
            channel=ChannelKind.TELEGRAM,
            channel_user_id=ChannelUserId("42"),
            text=MessageText(text),
        ),
        target=ChannelDeliveryTarget(
            channel=ChannelKind.TELEGRAM,
            channel_user_id=ChannelUserId("42"),
        ),
    )


class TwoMessages(UseCaseContract[str, list[ChannelInboundDelivery]]):
    def run(self, input_data: str) -> list[ChannelInboundDelivery]:
        return [delivery("boom"), delivery("hello")]


class FlakyPipeline(CustomerMessagePipelineContract):
    def start(self, input_data: InboundMessage) -> AssistantReply:
        if str(input_data.text) == "boom":
            raise RuntimeError("a bug in a tool")

        return AssistantReply(
            conversation_id=ConversationId(),
            text=MessageText("Hi!"),
            language=LanguageTag("en"),
            is_handed_off=False,
        )


class RecordingDelivery(UseCaseContract[ChannelReplyDelivery, DeliveredMessageCount]):
    def __init__(self, is_failing: bool = False) -> None:
        self.sent: list[str] = []
        self.is_failing: bool = is_failing

    def run(self, input_data: ChannelReplyDelivery) -> DeliveredMessageCount:
        if self.is_failing:
            raise RuntimeError("socket closed")

        self.sent.append(str(input_data.text))
        return DeliveredMessageCount(1)


def test_an_unexpected_error_of_one_message_spares_the_others() -> None:
    sender = RecordingDelivery()
    orchestrator = ChannelWebhookOrchestrator[str](
        TwoMessages(), FlakyPipeline(), sender
    )

    outcome = orchestrator.execute("update")

    assert (outcome.received, outcome.answered, outcome.failed) == (2, 1, 1)
    assert sender.sent == ["Hi!"]


def test_an_unexpected_delivery_error_is_counted_not_raised() -> None:
    orchestrator = ChannelWebhookOrchestrator[str](
        TwoMessages(), FlakyPipeline(), RecordingDelivery(is_failing=True)
    )

    outcome = orchestrator.execute("update")

    assert (outcome.answered, outcome.failed) == (0, 2)

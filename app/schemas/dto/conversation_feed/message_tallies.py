"""Message counts and model usage the database sums per conversation."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import (
    ConversationMessageCount,
    LlmTokenCount,
)


class ConversationMessageTally(ImmutableDTO):
    """How many messages a conversation has, and how many the customer wrote."""

    message_count: ConversationMessageCount = ConversationMessageCount(0)
    customer_message_count: ConversationMessageCount = ConversationMessageCount(0)


class ConversationUsageView(ImmutableDTO):
    """
    Language-model usage of a whole conversation (every message, also the
    ones a page of the transcript does not show).
    """

    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)

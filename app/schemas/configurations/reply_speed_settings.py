from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import (
    ChatTurnDeadlineSeconds,
    MessageCoalesceSeconds,
)

DEFAULT_MESSAGE_COALESCE_SECONDS: int = 3
DEFAULT_CHAT_TURN_DEADLINE_SECONDS: int = 20


class ReplySpeedSettings(ImmutableDTO):
    """
    How fast and how reliably customers of the messaging channels hear
    back: quick messages in a row wait MESSAGE_COALESCE_SECONDS of quiet and
    get one reply; a turn still running CHAT_TURN_DEADLINE_SECONDS after the
    customer's first message sends a short "one moment" once; and a model
    whose provider fails (or whose circuit is open) is replaced for the
    call by LLM_FALLBACK_MODEL_ID of the other provider (None: no failover).
    """

    message_coalesce_seconds: MessageCoalesceSeconds = MessageCoalesceSeconds(
        DEFAULT_MESSAGE_COALESCE_SECONDS
    )
    chat_turn_deadline_seconds: ChatTurnDeadlineSeconds = ChatTurnDeadlineSeconds(
        DEFAULT_CHAT_TURN_DEADLINE_SECONDS
    )
    llm_fallback_model_id: LlmModelId | None = None

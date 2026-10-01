import threading
import zlib

from app.contracts.conversation_flow import (
    ConversationTurnOrchestratorContract,
    CustomerMessagePipelineContract,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage

LOCK_STRIPE_COUNT: int = 256


class CustomerMessagePipeline(CustomerMessagePipelineContract):
    """
    The customer-message phase every channel gateway starts.

    Messages of one customer in one channel are answered one at a time, so
    their transcript turns keep consecutive sequence numbers and every reply
    sees the previous one. Different customers run in parallel (striped
    locks: memory stays bounded however many customers write).
    """

    def __init__(self, turn_orchestrator: ConversationTurnOrchestratorContract) -> None:
        self._turn_orchestrator: ConversationTurnOrchestratorContract = (
            turn_orchestrator
        )
        self._locks: tuple[threading.Lock, ...] = tuple(
            threading.Lock() for _ in range(LOCK_STRIPE_COUNT)
        )

    def start(self, input_data: InboundMessage) -> AssistantReply:
        with self._lock_for(input_data):
            return self._turn_orchestrator.execute(input_data)

    def _lock_for(self, message: InboundMessage) -> threading.Lock:
        key: str = f"{message.business_id}|{message.channel}|{message.channel_user_id}"
        return self._locks[zlib.crc32(key.encode()) % LOCK_STRIPE_COUNT]

from app.contracts.conversation_flow import (
    ConversationTurnOrchestratorContract,
    CustomerMessagePipelineContract,
)
from app.contracts.registries import CustomerMessageLockRegistryContract
from app.contracts.turn_slots import TurnSlotRegistryContract
from app.schemas.dto.conversations import AssistantReply, InboundMessage


class CustomerMessagePipeline(CustomerMessagePipelineContract):
    """
    The customer-message phase every channel gateway starts.

    Messages of one customer in one channel are answered one at a time
    across every API instance and worker (the customer's lock is held for
    the whole turn), so their transcript turns keep consecutive sequence
    numbers and every reply sees the previous one. Different customers run
    in parallel.

    A turn first takes one of the process's turn places, then the
    customer's lock: the lock holds a database connection for the whole
    turn, so a burst of turns waiting for the model (or a slow provider)
    waits for a place holding nothing, and the pool always keeps
    connections for everything else.
    """

    def __init__(
        self,
        turn_orchestrator: ConversationTurnOrchestratorContract,
        customer_locks: CustomerMessageLockRegistryContract,
        turn_slots: TurnSlotRegistryContract,
    ) -> None:
        self._turn_orchestrator: ConversationTurnOrchestratorContract = (
            turn_orchestrator
        )
        self._customer_locks: CustomerMessageLockRegistryContract = customer_locks
        self._turn_slots: TurnSlotRegistryContract = turn_slots

    def start(self, input_data: InboundMessage) -> AssistantReply:
        with (
            self._turn_slots.hold(),
            self._customer_locks.lock_for_customer(
                input_data.business_id,
                input_data.channel,
                input_data.channel_user_id,
            ),
        ):
            return self._turn_orchestrator.execute(input_data)

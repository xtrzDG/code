from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.turn_slots import TurnSlotRegistryContract
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.public_demo import (
    PublicDemoMessageCommand,
    PublicDemoReply,
    PublicDemoTurnOutcome,
)


class PublicDemoMessagePipeline(
    PipelineContract[PublicDemoMessageCommand, PublicDemoReply]
):
    """
    A landing-page visitor's message to a demo business: admitted (a demo
    business, within the demo limits), answered by the same conversation
    turn real customers get but in sandbox, and told back with what the
    turn did.

    The visitor waits for the answer in the request, so demo turns have
    places of their own (two per API process, `public_demo_slots`): the
    landing page never takes the threads or the model calls the owners'
    cabinets need; beyond them the visitor is asked to try again (429).
    """

    def __init__(
        self,
        admit_message: OrchestratorContract[PublicDemoMessageCommand, InboundMessage],
        turn_orchestrator: ConversationTurnOrchestratorContract,
        summarize_reply: OrchestratorContract[PublicDemoTurnOutcome, PublicDemoReply],
        public_demo_slots: TurnSlotRegistryContract,
    ) -> None:
        self._admit_message: OrchestratorContract[
            PublicDemoMessageCommand, InboundMessage
        ] = admit_message
        self._turn_orchestrator: ConversationTurnOrchestratorContract = (
            turn_orchestrator
        )
        self._summarize_reply: OrchestratorContract[
            PublicDemoTurnOutcome, PublicDemoReply
        ] = summarize_reply
        self._public_demo_slots: TurnSlotRegistryContract = public_demo_slots

    def start(self, input_data: PublicDemoMessageCommand) -> PublicDemoReply:
        message: InboundMessage = self._admit_message.execute(input_data)
        with self._public_demo_slots.hold():
            reply: AssistantReply = self._turn_orchestrator.execute(message)

        return self._summarize_reply.execute(
            PublicDemoTurnOutcome(business_id=message.business_id, reply=reply)
        )

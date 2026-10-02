from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.conversations import AssistantReply, InboundMessage


class OwnerTestChatPipeline(PipelineContract[OwnerTestChatCommand, AssistantReply]):
    """
    The owner's test chat: access check and version choice, then the same
    conversation turn real customers get (sandbox, OWNER_TEST channel).
    """

    def __init__(
        self,
        prepare_test_message: OrchestratorContract[
            OwnerTestChatCommand, InboundMessage
        ],
        turn_orchestrator: ConversationTurnOrchestratorContract,
    ) -> None:
        self._prepare_test_message: OrchestratorContract[
            OwnerTestChatCommand, InboundMessage
        ] = prepare_test_message
        self._turn_orchestrator: ConversationTurnOrchestratorContract = (
            turn_orchestrator
        )

    def start(self, input_data: OwnerTestChatCommand) -> AssistantReply:
        message: InboundMessage = self._prepare_test_message.execute(input_data)
        return self._turn_orchestrator.execute(message)

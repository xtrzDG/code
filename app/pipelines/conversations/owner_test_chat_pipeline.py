from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.turn_slots import TurnSlotRegistryContract
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.setup.setup_progress import ActivationEventRecord
from app.schemas.typings.users.booleans import IsPlatformAdmin
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.conversations.platform_details import reply_for


class OwnerTestChatPipeline(PipelineContract[OwnerTestChatCommand, AssistantReply]):
    """
    The owner's test chat: a preview version when the owner's latest edits
    are not in any version yet, access check and version choice, then the
    same conversation turn real customers get (sandbox, OWNER_TEST
    channel). The first answered test message is the TEST_CHAT_TRIED
    milestone of the guided setup.

    The owner waits for the answer in the request, so the test chat has
    places of its own (TEST_CHAT_MAX_CONCURRENCY per API process): a few
    owners trying their assistants never take the threads the cabinet
    needs; beyond them the owner is asked to try again in a moment (429).
    The tool calls' inputs and results reach platform admins only.
    """

    def __init__(
        self,
        prepare_test_chat_version: OrchestratorContract[OwnerTestChatCommand, None],
        prepare_test_message: OrchestratorContract[
            OwnerTestChatCommand, InboundMessage
        ],
        turn_orchestrator: ConversationTurnOrchestratorContract,
        record_activation_event: OrchestratorContract[ActivationEventRecord, None],
        test_chat_slots: TurnSlotRegistryContract,
        see_platform_details: OrchestratorContract[UserId, IsPlatformAdmin]
        | None = None,
    ) -> None:
        self._see_platform_details: (
            OrchestratorContract[UserId, IsPlatformAdmin] | None
        ) = see_platform_details
        self._prepare_test_chat_version: OrchestratorContract[
            OwnerTestChatCommand, None
        ] = prepare_test_chat_version
        self._prepare_test_message: OrchestratorContract[
            OwnerTestChatCommand, InboundMessage
        ] = prepare_test_message
        self._turn_orchestrator: ConversationTurnOrchestratorContract = (
            turn_orchestrator
        )
        self._record_activation_event: OrchestratorContract[
            ActivationEventRecord, None
        ] = record_activation_event
        self._test_chat_slots: TurnSlotRegistryContract = test_chat_slots

    def start(self, input_data: OwnerTestChatCommand) -> AssistantReply:
        with self._test_chat_slots.hold():
            self._prepare_test_chat_version.execute(input_data)
            message: InboundMessage = self._prepare_test_message.execute(input_data)
            reply: AssistantReply = self._turn_orchestrator.execute(message)

        self._record_activation_event.execute(
            ActivationEventRecord(
                business_id=input_data.business_id,
                kind=ActivationEventKind.TEST_CHAT_TRIED,
            )
        )
        return reply_for(
            reply,
            self._see_platform_details is not None
            and self._see_platform_details.execute(input_data.user_id),
        )

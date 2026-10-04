"""
Recording fakes of the conversation engine, the voice platform, the call
greeting, the tool catalog and token login, programmable by tests.
"""

from collections.abc import Callable

from app.contracts.assistant_assembly import AssistantToolCatalogContract
from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.conversations import (
    AssistantReply,
    CallGreeting,
    CallGreetingRequest,
    InboundMessage,
    LlmToolDefinition,
)
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import SessionCheck
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    VoiceAgentId,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from tests.foundation.access_support import signed_in

NO_COST: CostMicroUsd = CostMicroUsd(0)


type ReplyResponder = Callable[[InboundMessage, int], AssistantReply]


class FakeConversationTurnOrchestrator(ConversationTurnOrchestratorContract):
    """
    Answers sandbox messages with a programmable responder. One conversation
    per channel user; every reply is stored as a message with `reply_cost`
    so autotests can sum the assistant's costs.
    """

    def __init__(
        self,
        responder: ReplyResponder,
        message_repo: MessageRepoContract,
        reply_cost: CostMicroUsd = NO_COST,
    ) -> None:
        self._responder: ReplyResponder = responder
        self._message_repo: MessageRepoContract = message_repo
        self._reply_cost: CostMicroUsd = reply_cost
        self._conversation_ids: dict[str, ConversationId] = {}
        self._turn_counts: dict[str, int] = {}
        self.inbound_messages: list[InboundMessage] = []

    def conversation_id_for(self, channel_user_id: str) -> ConversationId:
        return self._conversation_ids.setdefault(channel_user_id, ConversationId())

    def execute(self, input_data: InboundMessage) -> AssistantReply:
        self.inbound_messages.append(input_data)
        channel_user_id: str = str(input_data.channel_user_id)
        turn_index: int = self._turn_counts.get(channel_user_id, 0)
        self._turn_counts[channel_user_id] = turn_index + 1
        reply: AssistantReply = self._responder(input_data, turn_index)
        conversation_id: ConversationId = self.conversation_id_for(channel_user_id)
        reply = reply.model_copy(update={"conversation_id": conversation_id})
        self._message_repo.save(
            MessageDocument(
                conversation_id=conversation_id,
                business_id=input_data.business_id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.ASSISTANT,
                text=reply.text or MessageText("(silent)"),
                cost_micro_usd=self._reply_cost,
            )
        )
        return reply


class FakeVoiceAgentProvisioner(VoiceAgentProvisionerAdapterContract):
    """Records every spec; returns the existing agent id or a new one."""

    def __init__(self) -> None:
        self.specs: list[VoiceAgentSpec] = []
        self.removed_agent_ids: list[VoiceAgentId] = []
        self.error: ExternalServiceError | None = None
        self.missing_settings: list[EnvironmentVariableName] = []
        self._created_count: int = 0

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        return list(self.missing_settings)

    def remove_agent(self, agent_id: VoiceAgentId) -> None:
        self.removed_agent_ids.append(agent_id)

    def upsert_agent(self, spec: VoiceAgentSpec) -> VoiceAgentId:
        self.specs.append(spec)
        if self.error is not None:
            raise self.error

        if spec.existing_agent_id is not None:
            return spec.existing_agent_id

        self._created_count += 1
        return VoiceAgentId(f"agent_{self._created_count}")


class FakeCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    """First phrase of a call; unknown languages fall back to English."""

    def __init__(self) -> None:
        self.requests: list[CallGreetingRequest] = []
        self.error: NotFoundError | None = None

    def run(self, input_data: CallGreetingRequest) -> CallGreeting:
        self.requests.append(input_data)
        if self.error is not None:
            raise self.error

        language: LanguageTag = input_data.language or LanguageTag("en")
        return CallGreeting(
            text=MessageText(f"[{language}] AI assistant here; the call is recorded."),
            language=language,
        )


class FakeAssistantToolCatalog(AssistantToolCatalogContract):
    """One trivial definition per tool, in the requested order."""

    def list_definitions(
        self,
        tool_names: list[AssistantToolName],
    ) -> list[LlmToolDefinition]:
        return [
            LlmToolDefinition(
                name=tool_name,
                description=LlmToolDescription(f"The {tool_name.value} tool."),
                input_schema_json=LlmToolInputSchemaJson('{"type": "object"}'),
            )
            for tool_name in tool_names
        ]


class FakeAuthenticationOperator(OperatorContract[SessionCheck, SessionAssurance]):
    """Bearer tokens are "token-<user id>"."""

    def __init__(self) -> None:
        self._users: dict[str, UserId] = {}

    def register(self, user_id: UserId) -> str:
        token: str = f"token-{user_id}"
        self._users[token] = user_id
        return token

    def operate(self, input_data: SessionCheck) -> SessionAssurance:
        token: AccessToken = input_data.access_token
        user_id: UserId | None = self._users.get(str(token))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return signed_in(user_id)

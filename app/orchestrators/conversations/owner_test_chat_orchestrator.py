from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.owner_test_chat import (
    OwnerTestChatCommand,
    OwnerTestChatVersionQuery,
)
from app.schemas.dto.conversations import InboundMessage
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.conversations.strings import ChannelUserId

DEFAULT_SESSION_KEY: str = "default"


class OwnerTestChatOrchestrator(
    OrchestratorContract[OwnerTestChatCommand, InboundMessage]
):
    """
    Turn an owner's test chat message into a sandbox customer message
    (concept section 8, /assistant "test chat"): check that the user may act
    on the business (owners and staff), choose the version to test, and
    address the message to the OWNER_TEST channel of this user and session,
    so tests never mix with real customers, billing or staff notifications.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        resolve_test_chat_version: UseCaseContract[
            OwnerTestChatVersionQuery, AssistantVersionId
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._resolve_test_chat_version: UseCaseContract[
            OwnerTestChatVersionQuery, AssistantVersionId
        ] = resolve_test_chat_version

    def execute(self, input_data: OwnerTestChatCommand) -> InboundMessage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        if str(input_data.request.text).strip() == "":
            raise ValidationFailedError("The test message is empty.")

        version_id: AssistantVersionId = self._resolve_test_chat_version.run(
            OwnerTestChatVersionQuery(
                business_id=business.id,
                requested_version_id=input_data.request.assistant_version_id,
                published_version_id=business.published_assistant_version_id,
            )
        )
        session_key: str = (
            DEFAULT_SESSION_KEY
            if input_data.request.session_key is None
            else str(input_data.request.session_key)
        )
        return InboundMessage(
            business_id=business.id,
            channel=ChannelKind.OWNER_TEST,
            channel_user_id=ChannelUserId(f"owner:{input_data.user_id}:{session_key}"),
            text=input_data.request.text,
            is_sandbox=True,
            assistant_version_id=version_id,
        )

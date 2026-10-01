from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AssistantVersionRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.assistant_tools import AssistantToolContext
from app.schemas.dto.conversations import VoiceToolCallRequest
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.tool_selection import select_available_tools


class OpenVoiceConversationUseCase(
    UseCaseContract[VoiceToolCallRequest, AssistantToolContext]
):
    """
    Find or start the conversation of a phone call for a voice-agent tool
    call (concept section 7: the agent's tools are our webhooks).

    One conversation per provider call id, pinned to the version published
    when the call started. The caller is the contact with the caller's phone
    (or, for a withheld number, the one known by this call); the business
    comes from the verified webhook, never from the agent's arguments. The
    business status is not checked here: a call in progress keeps its tools,
    and the voice agent itself exists only while the business is live.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: VoiceToolCallRequest) -> AssistantToolContext:
        now: Microseconds = self._wall_clock.now_unix()
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        call_user_id = ChannelUserId(str(input_data.provider_call_id))
        conversation: ConversationDocument | None = self._find_call_conversation(
            business, call_user_id
        )
        contact: ContactDocument = self._resolve_contact(
            business, input_data, conversation, call_user_id, now
        )
        if conversation is None:
            version_id: AssistantVersionId | None = (
                business.published_assistant_version_id
            )
            if version_id is None:
                raise ConflictError(
                    f"{business.name} has no published assistant version yet."
                )

            conversation = ConversationDocument(
                business_id=business.id,
                contact_id=contact.id,
                assistant_version_id=version_id,
                channel=ChannelKind.PHONE,
                channel_user_id=call_user_id,
                last_message_at=now,
                created_at=now,
                updated_at=now,
            )

        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, conversation.assistant_version_id
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {conversation.assistant_version_id} was not found."
            )

        language: LanguageTag = (
            input_data.language
            if input_data.language is not None
            else conversation.language
            if conversation.language is not None
            else version.default_language
        )
        conversation.language = language
        conversation.last_message_at = now
        conversation.updated_at = now
        self._conversation_repo.save(conversation)
        return AssistantToolContext(
            business_id=business.id,
            business_country_code=business.country_code,
            contact_id=contact.id,
            contact_name=contact.name,
            contact_phone_number=contact.phone_number,
            verified_phone_number=input_data.caller_phone_number,
            conversation_id=conversation.id,
            channel=ChannelKind.PHONE,
            language=language,
            is_sandbox=conversation.is_sandbox,
            available_tools=select_available_tools(version, business),
        )

    def _find_call_conversation(
        self,
        business: BusinessDocument,
        call_user_id: ChannelUserId,
    ) -> ConversationDocument | None:
        for conversation in self._conversation_repo.list_by_business(business.id):
            if (
                conversation.channel is ChannelKind.PHONE
                and conversation.channel_user_id == call_user_id
            ):
                return conversation

        return None

    def _resolve_contact(
        self,
        business: BusinessDocument,
        request: VoiceToolCallRequest,
        conversation: ConversationDocument | None,
        call_user_id: ChannelUserId,
        now: Microseconds,
    ) -> ContactDocument:
        contact: ContactDocument | None = None
        if conversation is not None:
            contact = self._contact_repo.get(business.id, conversation.contact_id)

        if contact is None and request.caller_phone_number is not None:
            # Only a contact whose phone a channel proved is the caller.
            contact = self._contact_repo.find_by_verified_phone_number(
                business.id, request.caller_phone_number
            )

        identity = ChannelIdentity(
            channel=ChannelKind.PHONE,
            channel_user_id=(
                ChannelUserId(str(request.caller_phone_number))
                if request.caller_phone_number is not None
                else call_user_id
            ),
        )
        if contact is None:
            contact = self._contact_repo.find_by_channel_identity(
                business.id, identity.channel, identity.channel_user_id
            )

        if contact is None:
            contact = ContactDocument(
                business_id=business.id,
                phone_number=request.caller_phone_number,
                verified_phone_number=request.caller_phone_number,
                channel_identities=[identity],
                created_at=now,
                updated_at=now,
            )
            self._contact_repo.save(contact)
        elif (
            request.caller_phone_number is not None
            and contact.verified_phone_number != request.caller_phone_number
        ):
            contact.verified_phone_number = request.caller_phone_number
            contact.updated_at = now
            self._contact_repo.save(contact)

        return contact

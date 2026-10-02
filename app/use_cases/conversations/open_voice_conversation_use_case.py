from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
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
from app.utilities.channels.caller_reachability import list_reachable_identities
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.voice_service import find_voice_refusal
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
    comes from the verified webhook, never from the agent's arguments. A
    call in progress keeps its tools; a new call is refused (ConflictError)
    while the phone assistant is off (business not live, no voice in the
    live version or the plan, phone number disconnected). The tools learn
    whether a connected messenger reaches the caller: only then are the
    links the agent promises texted after the call.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        channel_repo: ChannelRepoContract,
        plan_registry: PlanRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._plan_registry: PlanRegistryContract = plan_registry
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
        if conversation is None:
            self._require_voice_service(business)

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
            business_timezone=business.timezone,
            can_text_caller=bool(
                list_reachable_identities(self._channel_repo, business.id, contact)
            ),
        )

    def _find_call_conversation(
        self,
        business: BusinessDocument,
        call_user_id: ChannelUserId,
    ) -> ConversationDocument | None:
        conversations: list[ConversationDocument] = (
            self._conversation_repo.list_by_channel_user(
                business.id, ChannelKind.PHONE, call_user_id
            )
        )
        return conversations[0] if conversations else None

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

    def _require_voice_service(self, business: BusinessDocument) -> None:
        published_version: AssistantVersionDocument | None = (
            None
            if business.published_assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, business.published_assistant_version_id
            )
        )
        refusal: str | None = find_voice_refusal(
            business,
            published_version,
            self._plan_registry.get(business.plan_key),
            find_business_channel(self._channel_repo, business.id, ChannelKind.PHONE),
        )
        if refusal is not None:
            raise ConflictError(refusal)

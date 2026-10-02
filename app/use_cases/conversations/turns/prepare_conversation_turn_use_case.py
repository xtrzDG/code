from datetime import datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LanguageDetectorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistant_tools import AssistantToolContext
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.conversations import InboundMessage
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.conversations.booleans import IsAfterHours
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.conversations.turns.contact_resolution import (
    resolve_contact,
)
from app.use_cases.conversations.turns.conversation_resolution import (
    resolve_conversation,
)
from app.use_cases.conversations.turns.inbound_message_rules import (
    is_sandbox_message,
    remove_nul_characters,
)
from app.use_cases.conversations.turns.turn_gate import choose_turn_gate
from app.use_cases.conversations.turns.turn_time import to_local_datetime
from app.utilities.conversations.opening_hours import is_open_at
from app.utilities.conversations.tool_selection import select_available_tools
from app.utilities.conversations.turn_context import TurnContext, build_context_line

# Longer messages are cut: no customer needs more, and tokens cost money.
MAX_CUSTOMER_TEXT_LENGTH: int = 4000


class PrepareConversationTurnUseCase(UseCaseContract[InboundMessage, PreparedTurn]):
    """
    Find everything one customer message belongs to and store it.

    1. The business; real messages need a LIVE business (sandbox and owner
       test messages do not).
    2. The contact by channel identity, then by a phone the channel proved
       (only a contact whose own phone is proved the same way; never for
       sandbox messages), else a new one; missing name, phone and identity
       are added, and a phone the channel proved is remembered as verified.
    3. The conversation of the contact in this channel and sandbox mode that
       staff still own (HANDOFF, however long ago, so the bot stays silent
       until the handoff is closed), else one with a message in the last 24
       hours, pinned to its assistant version; a message asking for another
       version, or no open conversation, starts a new one pinned to the
       requested or published version (ConflictError when the business has
       none).
    4. The gate: staff own a conversation in HANDOFF (silence in chat, a
       call-back promise on the phone); past the hourly per-contact limit the
       assistant answers once with a stop message, then stays silent.
    5. The language among the version's languages (fallback: the
       conversation's, then the version default), the after-hours flag from
       the profile hours in the business time zone, the inbound message and
       the context line for the model.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        language_detector: LanguageDetectorContract,
        wall_clock: WallClock[Microseconds],
        contact_message_limit: ContactMessageLimit,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._language_detector: LanguageDetectorContract = language_detector
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._contact_message_limit: ContactMessageLimit = contact_message_limit

    def run(self, input_data: InboundMessage) -> PreparedTurn:
        input_data = remove_nul_characters(input_data)
        now: Microseconds = self._wall_clock.now_unix()
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        is_sandbox: bool = is_sandbox_message(input_data)
        if not is_sandbox and business.status is not BusinessStatus.LIVE:
            raise ConflictError(f"The assistant of {business.name} is not live.")

        contact: ContactDocument = resolve_contact(
            self._contact_repo, business, input_data, is_sandbox, now
        )
        conversation, is_new_conversation = resolve_conversation(
            self._conversation_repo,
            self._assistant_version_repo,
            business,
            contact,
            input_data,
            is_sandbox,
            now,
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, conversation.assistant_version_id
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {conversation.assistant_version_id} was not found."
            )

        gate: TurnGate = choose_turn_gate(
            self._conversation_repo,
            self._message_repo,
            self._contact_message_limit,
            business,
            contact,
            conversation,
            now,
        )
        customer_text = MessageText(str(input_data.text)[:MAX_CUSTOMER_TEXT_LENGTH])
        language: LanguageTag = self._language_detector.detect(
            str(customer_text),
            list(version.languages),
            (
                conversation.language
                if conversation.language is not None
                else version.default_language
            ),
        )
        local_now: datetime = to_local_datetime(now, business)
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        is_open: bool | None = (
            None
            if profile is None
            else is_open_at(
                local_now,
                list(profile.hours),
                self._schedule_exception_repo.list_by_business(business.id),
            )
        )
        is_first_reply: bool = not self._has_assistant_reply(business, conversation)
        self._message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=business.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=customer_text,
                language=language,
                created_at=now,
                updated_at=now,
            )
        )
        conversation.language = language
        conversation.is_after_hours = IsAfterHours(is_open is False)
        conversation.last_message_at = now
        conversation.updated_at = now
        self._conversation_repo.save(conversation)
        if contact.language is None:
            contact.language = language
            contact.updated_at = now
            self._contact_repo.save(contact)

        available_tools: list[AssistantToolName] = select_available_tools(
            version, business
        )
        return PreparedTurn(
            business=business,
            version=version,
            contact=contact,
            conversation=conversation,
            language=language,
            gate=gate,
            is_new_conversation=is_new_conversation,
            is_first_reply=is_first_reply,
            customer_text=customer_text,
            context_line=MessageText(
                build_context_line(
                    TurnContext(
                        business_name=str(business.name),
                        timezone_name=str(business.timezone),
                        local_now=local_now,
                        channel=conversation.channel,
                        customer_name=None
                        if contact.name is None
                        else str(contact.name),
                        customer_phone_number=(
                            None
                            if contact.phone_number is None
                            else str(contact.phone_number)
                        ),
                        is_after_hours=is_open is False,
                        is_leads_only=business.service_mode is ServiceMode.LEADS_ONLY,
                        is_first_reply=(
                            is_first_reply
                            and conversation.channel is not ChannelKind.PHONE
                        ),
                    )
                )
            ),
            tool_context=AssistantToolContext(
                business_id=business.id,
                business_country_code=business.country_code,
                contact_id=contact.id,
                contact_name=contact.name,
                contact_phone_number=contact.phone_number,
                verified_phone_number=(
                    None
                    if conversation.is_sandbox
                    else input_data.contact_phone_number
                    or contact.verified_phone_number
                ),
                conversation_id=conversation.id,
                channel=conversation.channel,
                language=language,
                is_sandbox=conversation.is_sandbox,
                available_tools=available_tools,
                business_timezone=business.timezone,
            ),
            received_at=now,
        )

    def _has_assistant_reply(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
    ) -> bool:
        return (
            int(
                self._message_repo.count_by_conversation(
                    business.id,
                    conversation.id,
                    MessageDirection.OUTBOUND,
                    author=MessageAuthor.ASSISTANT,
                )
            )
            > 0
        )

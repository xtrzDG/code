from datetime import datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
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
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.reply_safety import InjectionSignal
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.customer_memory.returning_customers import (
    CustomerMemory,
    CustomerMemoryRequest,
)
from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.conversations.booleans import IsAfterHours
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
    InjectionFlagLimit,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.conversations.turns.contact_resolution import (
    resolve_contact,
)
from app.use_cases.conversations.turns.inbound_message_rules import (
    is_sandbox_message,
    remove_nul_characters,
)
from app.use_cases.conversations.turns.prepared_turn_parts import (
    build_tool_context,
    build_turn_context_line,
    has_assistant_reply,
    is_business_open,
    touch_conversation,
    turn_events,
)
from app.use_cases.conversations.turns.turn_gate import choose_turn_gate
from app.use_cases.conversations.turns.turn_language import (
    detect_turn_language,
    remember_contact_language,
)
from app.use_cases.shared.conversation_resolution import (
    resolve_conversation,
)
from app.use_cases.shared.turn_time import to_local_datetime
from app.utilities.conversations.tool_selection import select_available_tools
from app.utilities.media.attachment_texts import (
    describe_message_for_model,
    has_readable_content,
    readable_message_text,
)
from app.utilities.reply_guard.injection_signals import detect_injection

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
       call-back promise on the phone); a message that looks like prompt
       injection is flagged on the stored message, and a contact with
       INJECTION_FLAG_LIMIT flagged messages in a day, or past the hourly
       per-contact limit, is answered once with a stop message, then the
       assistant stays silent.
    5. The customer's language, any language (`detect_any`: a message that
       tells too little keeps the conversation's, then the contact's, then
       the version default language), the after-hours flag from
       the profile hours in the business time zone, the inbound message and
       the context line for the model. A message with nothing the assistant
       can read (a sticker, a file, a voice note without words) is answered
       with the platform's request to write (ATTACHMENT_NOTICE); voice-note
       transcripts and places count as what the customer said.
    6. The customer memory (`RecallCustomerMemoryUseCase`): a returning
       customer's memory joins the context line of the first reply only.
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
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        contact_message_limit: ContactMessageLimit,
        injection_flag_limit: InjectionFlagLimit,
        recall_customer_memory: UseCaseContract[CustomerMemoryRequest, CustomerMemory],
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
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._contact_message_limit: ContactMessageLimit = contact_message_limit
        self._injection_flag_limit: InjectionFlagLimit = injection_flag_limit
        self._recall_customer_memory: UseCaseContract[
            CustomerMemoryRequest, CustomerMemory
        ] = recall_customer_memory

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
        previous_last_message_at: Microseconds | None = (
            None if is_new_conversation else conversation.last_message_at
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, conversation.assistant_version_id
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {conversation.assistant_version_id} was not found."
            )

        written_text = MessageText(str(input_data.text)[:MAX_CUSTOMER_TEXT_LENGTH])
        attachments: list[MessageAttachment] = list(input_data.attachments)
        customer_text = MessageText(readable_message_text(written_text, attachments))
        injection_flag: InjectionSignal | None = detect_injection(str(customer_text))
        gate: TurnGate = choose_turn_gate(
            self._conversation_repo,
            self._message_repo,
            self._contact_message_limit,
            business,
            contact,
            conversation,
            now,
            injection_flag,
            self._injection_flag_limit,
        )
        if gate is TurnGate.ANSWER and not has_readable_content(
            written_text, attachments
        ):
            gate = TurnGate.ATTACHMENT_NOTICE

        detected: DetectedLanguage = detect_turn_language(
            self._language_detector, customer_text, version, conversation, contact
        )
        language: LanguageTag = detected.language
        local_now: datetime = to_local_datetime(now, business)
        is_open: bool | None = is_business_open(
            self._business_profile_repo,
            self._schedule_exception_repo,
            business,
            local_now,
        )
        is_first_reply: bool = not has_assistant_reply(
            self._message_repo, business, conversation
        )
        self._message_repo.save(
            MessageDocument(
                # The inbox's id: a turn run again stores the message once.
                id=input_data.customer_message_id or MessageId(),
                conversation_id=conversation.id,
                business_id=business.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=written_text,
                language=language,
                attachments=attachments,
                injection_flag=injection_flag,
                created_at=now,
                updated_at=now,
            )
        )
        touch_conversation(conversation, language, IsAfterHours(is_open is False), now)
        self._conversation_repo.save(conversation)
        for event in turn_events(is_new_conversation):
            self._live_events.publish(
                business.id,
                event,
                (conversation.id,),
                is_sandbox=conversation.is_sandbox,
            )
        remember_contact_language(self._contact_repo, contact, detected, now)
        memory: CustomerMemory = self._recall_customer_memory.run(
            CustomerMemoryRequest(
                business=business,
                contact=contact,
                conversation=conversation,
                is_new_conversation=is_new_conversation,
                previous_last_message_at=previous_last_message_at,
                wants_context=is_first_reply and gate is TurnGate.ANSWER,
                now=now,
            )
        )
        return PreparedTurn(
            business=business,
            version=version,
            contact=contact,
            conversation=conversation,
            reply_language=language,
            script_hint=detected.script_hint,
            gate=gate,
            is_new_conversation=is_new_conversation,
            is_first_reply=is_first_reply,
            customer_text=customer_text,
            model_text=MessageText(
                describe_message_for_model(written_text, attachments)
            ),
            attachments=attachments,
            reply_message_id=input_data.reply_message_id,
            context_line=build_turn_context_line(
                business,
                contact,
                conversation,
                detected,
                local_now,
                is_open is False,
                is_first_reply,
                memory,
            ),
            tool_context=build_tool_context(
                business,
                contact,
                conversation,
                input_data,
                language,
                select_available_tools(version, business),
            ),
            received_at=now,
        )

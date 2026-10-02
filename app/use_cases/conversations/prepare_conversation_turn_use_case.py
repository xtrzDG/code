from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

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
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistant_tools import AssistantToolContext
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.conversations import InboundMessage
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsAfterHours
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.opening_hours import is_open_at
from app.utilities.conversations.tool_selection import select_available_tools
from app.utilities.conversations.turn_context import TurnContext, build_context_line

MICROSECONDS_PER_SECOND: int = 1_000_000
CONVERSATION_WINDOW: timedelta = timedelta(hours=24)
CONTACT_LIMIT_WINDOW: timedelta = timedelta(hours=1)
# Longer messages are cut: no customer needs more, and tokens cost money.
MAX_CUSTOMER_TEXT_LENGTH: int = 4000
UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)
NUL_CHARACTER: str = "\x00"


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

        contact: ContactDocument = self._resolve_contact(
            business, input_data, is_sandbox, now
        )
        conversation, is_new_conversation = self._resolve_conversation(
            business, contact, input_data, is_sandbox, now
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id, conversation.assistant_version_id
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {conversation.assistant_version_id} was not found."
            )

        gate: TurnGate = self._choose_gate(business, contact, conversation, now)
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
            ),
            received_at=now,
        )

    def _resolve_contact(
        self,
        business: BusinessDocument,
        message: InboundMessage,
        is_sandbox: bool,
        now: Microseconds,
    ) -> ContactDocument:
        contact: ContactDocument | None = self._contact_repo.find_by_channel_identity(
            business.id, message.channel, message.channel_user_id
        )
        if (
            contact is None
            and not is_sandbox
            and message.contact_phone_number is not None
        ):
            # Only a contact whose phone a channel proved is the same person;
            # a phone someone typed into a chat proves nothing.
            contact = self._contact_repo.find_by_verified_phone_number(
                business.id, message.contact_phone_number
            )

        identity = ChannelIdentity(
            channel=message.channel,
            channel_user_id=message.channel_user_id,
        )
        if contact is None:
            contact = ContactDocument(
                business_id=business.id,
                name=message.contact_name,
                phone_number=message.contact_phone_number,
                verified_phone_number=(
                    None if is_sandbox else message.contact_phone_number
                ),
                channel_identities=[identity],
                created_at=now,
                updated_at=now,
            )
            self._contact_repo.save(contact)
            return contact

        is_changed: bool = False
        if identity not in contact.channel_identities:
            contact.channel_identities.append(identity)
            is_changed = True

        if contact.name is None and message.contact_name is not None:
            contact.name = message.contact_name
            is_changed = True

        if contact.phone_number is None and message.contact_phone_number is not None:
            contact.phone_number = message.contact_phone_number
            is_changed = True

        if (
            not is_sandbox
            and message.contact_phone_number is not None
            and contact.verified_phone_number != message.contact_phone_number
        ):
            contact.verified_phone_number = message.contact_phone_number
            is_changed = True

        if is_changed:
            contact.updated_at = now
            self._contact_repo.save(contact)

        return contact

    def _resolve_conversation(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        message: InboundMessage,
        is_sandbox: bool,
        now: Microseconds,
    ) -> tuple[ConversationDocument, bool]:
        open_conversation: ConversationDocument | None = self._find_open_conversation(
            business, contact, message.channel, is_sandbox, now
        )
        requested_version_id: AssistantVersionId | None = message.assistant_version_id
        if open_conversation is not None and (
            requested_version_id is None
            or requested_version_id == open_conversation.assistant_version_id
        ):
            return open_conversation, False

        version_id: AssistantVersionId | None = (
            requested_version_id
            if requested_version_id is not None
            else business.published_assistant_version_id
        )
        if version_id is None:
            raise ConflictError(
                f"{business.name} has no published assistant version yet."
            )

        if self._assistant_version_repo.get(business.id, version_id) is None:
            raise NotFoundError(f"Assistant version {version_id} was not found.")

        conversation = ConversationDocument(
            business_id=business.id,
            contact_id=contact.id,
            assistant_version_id=version_id,
            channel=message.channel,
            channel_user_id=message.channel_user_id,
            is_sandbox=is_sandbox,
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        self._conversation_repo.save(conversation)
        return conversation, True

    def _find_open_conversation(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        channel: ChannelKind,
        is_sandbox: bool,
        now: Microseconds,
    ) -> ConversationDocument | None:
        window_start: int = int(now) - to_microseconds(CONVERSATION_WINDOW)
        recent: ConversationDocument | None = None
        for conversation in self._conversation_repo.list_by_business(business.id):
            if (
                conversation.contact_id != contact.id
                or conversation.channel is not channel
                or conversation.is_sandbox != is_sandbox
                or conversation.status is ConversationStatus.CLOSED
            ):
                continue

            # Staff own it until they close the handoff, however long ago.
            if conversation.status is ConversationStatus.HANDOFF:
                return conversation

            if recent is None and int(conversation.last_message_at) >= window_start:
                recent = conversation

        return recent

    def _choose_gate(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        conversation: ConversationDocument,
        now: Microseconds,
    ) -> TurnGate:
        if conversation.status is ConversationStatus.HANDOFF:
            return (
                TurnGate.STAFF_CALLBACK
                if conversation.channel is ChannelKind.PHONE
                else TurnGate.STAFF_SILENCE
            )

        recent_message_count: int = self._count_recent_inbound_messages(
            business, contact, now
        )
        if recent_message_count == int(self._contact_message_limit):
            return TurnGate.LIMIT_NOTICE

        if recent_message_count > int(self._contact_message_limit):
            return TurnGate.LIMIT_SILENCE

        return TurnGate.ANSWER

    def _count_recent_inbound_messages(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        now: Microseconds,
    ) -> int:
        """Inbound messages of the contact in the last hour, in every channel."""

        window_start: int = int(now) - to_microseconds(CONTACT_LIMIT_WINDOW)
        recent_message_count: int = 0
        for conversation in self._conversation_repo.list_by_business(business.id):
            if conversation.contact_id != contact.id:
                continue

            if int(conversation.last_message_at) < window_start:
                continue

            for message in self._message_repo.list_by_conversation(
                business.id, conversation.id
            ):
                if (
                    message.direction is MessageDirection.INBOUND
                    and int(message.created_at) >= window_start
                ):
                    recent_message_count += 1

        return recent_message_count

    def _has_assistant_reply(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
    ) -> bool:
        return any(
            message.direction is MessageDirection.OUTBOUND
            and message.author is MessageAuthor.ASSISTANT
            for message in self._message_repo.list_by_conversation(
                business.id, conversation.id
            )
        )


def remove_nul_characters(message: InboundMessage) -> InboundMessage:
    """
    The message without NUL characters in its text and name: no customer
    means them, and Postgres JSONB cannot store them, so keeping them would
    answer a message in memory and silently drop it on Postgres.
    """

    text: str = str(message.text)
    name: str | None = (
        None if message.contact_name is None else str(message.contact_name)
    )
    if NUL_CHARACTER not in text and (name is None or NUL_CHARACTER not in name):
        return message

    return message.model_copy(
        update={
            "text": MessageText(text.replace(NUL_CHARACTER, "")),
            "contact_name": (
                None
                if name is None or name.replace(NUL_CHARACTER, "").strip() == ""
                else ContactName(name.replace(NUL_CHARACTER, ""))
            ),
        }
    )


def is_sandbox_message(message: InboundMessage) -> bool:
    """Owner test chat and autotests never reach real customers or billing."""

    return message.is_sandbox or message.channel is ChannelKind.OWNER_TEST


def to_local_datetime(instant: Microseconds, business: BusinessDocument) -> datetime:
    """A UNIX instant as a wall-clock moment in the business time zone."""

    moment: datetime = UNIX_EPOCH + timedelta(microseconds=int(instant))
    return moment.astimezone(ZoneInfo(str(business.timezone)))


def to_microseconds(duration: timedelta) -> int:
    return int(duration.total_seconds() * MICROSECONDS_PER_SECOND)

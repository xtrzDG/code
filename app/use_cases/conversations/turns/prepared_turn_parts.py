"""The parts of a prepared turn that are built, not looked up."""

from datetime import datetime

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistant_tools import AssistantToolContext
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.customer_memory.returning_customers import CustomerMemory
from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.opening_hours import is_open_at
from app.utilities.conversations.reply_language import describe_reply_language
from app.utilities.conversations.returning_customer_lines import (
    describe_returning_customer,
)
from app.utilities.conversations.turn_context import TurnContext, build_context_line


def build_turn_context_line(
    business: BusinessDocument,
    contact: ContactDocument,
    conversation: ConversationDocument,
    detected: DetectedLanguage,
    local_now: datetime,
    is_after_hours: bool,
    is_first_reply: bool,
    memory: CustomerMemory,
) -> MessageText:
    """
    The server-written preamble of the model's user turn, with what the
    assistant remembers of a returning customer (only on the first reply,
    so the conversation's earlier turns, the cached prefix, never change).
    """

    return MessageText(
        build_context_line(
            TurnContext(
                business_name=str(business.name),
                timezone_name=str(business.timezone),
                local_now=local_now,
                channel=conversation.channel,
                reply_language_note=describe_reply_language(
                    detected.language, detected.script_hint
                ),
                customer_name=None if contact.name is None else str(contact.name),
                customer_phone_number=(
                    None if contact.phone_number is None else str(contact.phone_number)
                ),
                is_after_hours=is_after_hours,
                is_leads_only=business.service_mode is ServiceMode.LEADS_ONLY,
                is_first_reply=(
                    is_first_reply and conversation.channel is not ChannelKind.PHONE
                ),
                memory_lines=(
                    ()
                    if memory.context is None
                    else tuple(
                        describe_returning_customer(memory.context, business.timezone)
                    )
                ),
            )
        )
    )


def build_tool_context(
    business: BusinessDocument,
    contact: ContactDocument,
    conversation: ConversationDocument,
    message: InboundMessage,
    language: LanguageTag,
    available_tools: list[AssistantToolName],
) -> AssistantToolContext:
    """What the model's tools run with in this turn."""

    return AssistantToolContext(
        business_id=business.id,
        business_country_code=business.country_code,
        contact_id=contact.id,
        contact_name=contact.name,
        contact_phone_number=contact.phone_number,
        verified_phone_number=(
            None
            if conversation.is_sandbox
            else message.contact_phone_number or contact.verified_phone_number
        ),
        conversation_id=conversation.id,
        channel=conversation.channel,
        language=language,
        is_sandbox=conversation.is_sandbox,
        available_tools=available_tools,
        business_timezone=business.timezone,
    )


def touch_conversation(
    conversation: ConversationDocument,
    language: LanguageTag,
    is_after_hours: bool,
    now: Microseconds,
) -> None:
    """The conversation after a customer message: language, hours, time."""

    conversation.language = language
    conversation.is_after_hours = is_after_hours
    conversation.last_message_at = now
    conversation.updated_at = now


def has_assistant_reply(
    message_repo: MessageRepoContract,
    business: BusinessDocument,
    conversation: ConversationDocument,
) -> bool:
    """The assistant already answered in this conversation."""

    return (
        int(
            message_repo.count_by_conversation(
                business.id,
                conversation.id,
                MessageDirection.OUTBOUND,
                author=MessageAuthor.ASSISTANT,
            )
        )
        > 0
    )


def is_business_open(
    profile_repo: BusinessProfileRepoContract,
    exception_repo: ScheduleExceptionRepoContract,
    business: BusinessDocument,
    local_now: datetime,
) -> bool | None:
    """Open by the profile's hours and exceptions; None without a profile."""

    profile: BusinessProfileDocument | None = profile_repo.get_by_business(business.id)
    if profile is None:
        return None

    return is_open_at(
        local_now, list(profile.hours), exception_repo.list_by_business(business.id)
    )

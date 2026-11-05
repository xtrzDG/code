"""The caller's customer memory of a call: the call conversation's summary."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
    ConversationMemoryRepoContract,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.customer_memory.conversation_summaries import (
    ConversationSummaryWrite,
)
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.calls.booleans import IsCallRemembered
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.utilities.memory.assistant_settings_views import view_assistant_settings
from app.utilities.privacy.erased_conversations import is_erased_conversation


class CallMemory:
    """
    A call is remembered like a chat (the customer-and-AI concept: a
    returning caller is greeted as a returning chatter): its conversation
    gets the summary that `ReturningCustomerContext` reads on the caller's
    next conversation in any channel. Only for a business that remembers
    customers (Settings → General), a real conversation of a caller not
    erased, and once: a conversation already summarized since its latest
    message keeps its summary. The write is one step and only while the
    conversation is as read (an erasure meanwhile wins).
    """

    def __init__(
        self,
        conversation_repo: ConversationRepoContract,
        conversation_memory_repo: ConversationMemoryRepoContract,
        contact_repo: ContactRepoContract,
        assistant_settings_repo: AssistantSettingsRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._memory_repo: ConversationMemoryRepoContract = conversation_memory_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._settings_repo: AssistantSettingsRepoContract = assistant_settings_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def find_conversation(
        self, business: BusinessDocument, recorded: RecordedCall
    ) -> ConversationDocument | None:
        """The call's conversation when it should be remembered, else None."""

        if recorded.conversation_id is None or not (
            view_assistant_settings(
                self._settings_repo.get_by_business(business.id)
            ).remembers_customers
        ):
            return None

        conversation: ConversationDocument | None = self._conversation_repo.get(
            business.id, recorded.conversation_id
        )
        if (
            conversation is None
            or conversation.is_sandbox
            or is_erased_conversation(conversation)
            or (
                conversation.summarized_at is not None
                and int(conversation.summarized_at) >= int(conversation.last_message_at)
            )
        ):
            return None

        contact: ContactDocument | None = self._contact_repo.get(
            business.id, conversation.contact_id
        )
        if contact is None or contact.erased_at is not None:
            return None

        return conversation

    def remember(
        self,
        conversation: ConversationDocument,
        summary: ConversationSummaryText | None,
    ) -> IsCallRemembered:
        """Store the summary on the conversation; False when nothing was stored."""

        if summary is None:
            return False

        write = ConversationSummaryWrite(
            summary=summary,
            written_at=self._wall_clock.now_unix(),
            covers_until=conversation.last_message_at,
        )
        return (
            self._memory_repo.set_summary(
                conversation.business_id, conversation.id, write
            )
            is not None
        )

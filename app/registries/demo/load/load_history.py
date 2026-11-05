"""
The customers of a load business: one contact per conversation, chat
conversations spread over the last four months (ten messages each, the
assistant's with model usage and cost) and the website-widget visitors
chatting right now (two messages each).
"""

import random
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.registries.demo.load.load_lines import CUSTOMER_NAMES, lines_for
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.load_data import LoadVolumeRequest, LoadWidgetVisitor
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText

MESSAGES_PER_CONVERSATION: int = 10
MESSAGES_PER_VISITOR: int = 2
SECOND: int = 1_000_000
HOUR: int = 3_600 * SECOND
DAY: int = 24 * HOUR
HISTORY_DAYS: int = 120
# Conversation states in the history: mostly finished, some still open, a
# few handed to staff.
STATUS_WEIGHTS: dict[ConversationStatus, int] = {
    ConversationStatus.CLOSED: 85,
    ConversationStatus.OPEN: 12,
    ConversationStatus.HANDOFF: 3,
}
AFTER_HOURS_SHARE: float = 0.25


@dataclass
class LoadHistory:
    """What `build_history` returns, in the order it is stored."""

    contacts: list[ContactDocument] = field(default_factory=list[ContactDocument])
    conversations: list[ConversationDocument] = field(
        default_factory=list[ConversationDocument]
    )
    messages: list[MessageDocument] = field(default_factory=list[MessageDocument])
    visitors: list[LoadWidgetVisitor] = field(default_factory=list[LoadWidgetVisitor])


def conversation_sizes(message_count: int) -> list[int]:
    """Ten messages per conversation; the last one takes the remainder."""

    full, remainder = divmod(message_count, MESSAGES_PER_CONVERSATION)
    return [MESSAGES_PER_CONVERSATION] * full + ([remainder] if remainder else [])


class LoadHistoryBuilder:
    """Builds the conversations of one load business with one random source."""

    def __init__(self, request: LoadVolumeRequest, chooser: random.Random) -> None:
        self._request: LoadVolumeRequest = request
        self._chooser: random.Random = chooser
        self._now: int = int(request.now)
        self._language: str = str(request.business.default_language)
        self._customer_lines, self._assistant_lines = lines_for(self._language)
        self._channels: list[ChannelKind] = list(request.channel_kinds) or [
            ChannelKind.WEB_CHAT
        ]
        self.history: LoadHistory = LoadHistory()

    def build(self) -> LoadHistory:
        message_count: int = int(self._request.share.message_count)
        visitor_count: int = min(
            int(self._request.share.visitor_count),
            message_count // MESSAGES_PER_VISITOR,
        )
        sizes: list[int] = conversation_sizes(
            message_count - visitor_count * MESSAGES_PER_VISITOR
        )
        starts: list[int] = sorted(
            self._now - self._chooser.randrange(HOUR, HISTORY_DAYS * DAY) for _ in sizes
        )
        for size, start in zip(sizes, starts, strict=True):
            self._add_chat(size, start)

        for visitor_index in range(visitor_count):
            self._add_visitor(visitor_index)

        return self.history

    def _add_chat(self, size: int, start: int) -> None:
        channel: ChannelKind = self._chooser.choice(self._channels)
        user_id = ChannelUserId(
            f"{channel.value}-{self._chooser.randrange(10**9, 10**10)}"
        )
        contact: ContactDocument = self._add_contact(channel, user_id, start)
        status: ConversationStatus = self._chooser.choices(
            list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values())
        )[0]
        self._add_conversation(contact, channel, user_id, start, size, status)

    def _add_visitor(self, visitor_index: int) -> None:
        session_key = WidgetSessionKey(
            f"load_{int(self._request.random_seed)}_{visitor_index:05d}_"
            f"{self._chooser.randrange(16**8):08x}"
        )
        user_id = ChannelUserId(str(session_key))
        start: int = self._now - self._chooser.randrange(120, 3_600) * SECOND
        contact: ContactDocument = self._add_contact(
            ChannelKind.WEB_CHAT, user_id, start
        )
        conversation: ConversationDocument = self._add_conversation(
            contact,
            ChannelKind.WEB_CHAT,
            user_id,
            start,
            MESSAGES_PER_VISITOR,
            ConversationStatus.OPEN,
        )
        self.history.visitors.append(
            LoadWidgetVisitor(
                session_key=session_key,
                conversation_id=conversation.id,
                latest_message_id=self.history.messages[-1].id,
            )
        )

    def _add_contact(
        self, channel: ChannelKind, user_id: ChannelUserId, start: int
    ) -> ContactDocument:
        contact = ContactDocument(
            business_id=self._request.business.id,
            name=ContactName(self._chooser.choice(CUSTOMER_NAMES)),
            language=self._request.business.default_language,
            channel_identities=[
                ChannelIdentity(channel=channel, channel_user_id=user_id)
            ],
            created_at=Microseconds(start),
            updated_at=Microseconds(start),
        )
        self.history.contacts.append(contact)
        return contact

    def _add_conversation(
        self,
        contact: ContactDocument,
        channel: ChannelKind,
        user_id: ChannelUserId,
        start: int,
        size: int,
        status: ConversationStatus,
    ) -> ConversationDocument:
        conversation = ConversationDocument(
            business_id=self._request.business.id,
            contact_id=contact.id,
            assistant_version_id=self._request.assistant_version_id,
            channel=channel,
            channel_user_id=user_id,
            language=self._request.business.default_language,
            status=status,
            is_after_hours=self._chooser.random() < AFTER_HOURS_SHARE,
            last_message_at=Microseconds(start),
            created_at=Microseconds(start),
            updated_at=Microseconds(start),
        )
        moment: int = start
        for index in range(size):
            if index > 0:
                moment += self._chooser.randrange(15, 90) * SECOND
            self.history.messages.append(
                self._message(conversation, index, Microseconds(moment))
            )

        conversation.last_message_at = Microseconds(moment)
        conversation.updated_at = Microseconds(moment)
        self.history.conversations.append(conversation)
        return conversation

    def _message(
        self, conversation: ConversationDocument, index: int, moment: Microseconds
    ) -> MessageDocument:
        is_customer: bool = index % 2 == 0
        line_index: int = self._chooser.randrange(len(self._customer_lines))
        if is_customer:
            return MessageDocument(
                conversation_id=conversation.id,
                business_id=conversation.business_id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText(self._customer_lines[line_index]),
                language=conversation.language,
                created_at=moment,
                updated_at=moment,
            )

        input_tokens: int = self._chooser.randrange(1_800, 3_200)
        output_tokens: int = self._chooser.randrange(40, 220)
        return MessageDocument(
            conversation_id=conversation.id,
            business_id=conversation.business_id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.ASSISTANT,
            text=MessageText(self._assistant_lines[line_index]),
            language=conversation.language,
            model_id=self._request.model_id,
            input_tokens=LlmTokenCount(input_tokens),
            output_tokens=LlmTokenCount(output_tokens),
            # gpt-5-mini list prices: $0.25 in and $2 out per million tokens.
            cost_micro_usd=CostMicroUsd(
                (input_tokens * 25 + output_tokens * 200) // 100
            ),
            created_at=moment,
            updated_at=moment,
        )

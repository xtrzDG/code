"""
The customer's messages about a waiting deposit: the reminder halfway
through the hold (with the same link) and the word that a booking's place
was let go. Through the outbox, in the messenger the customer asked in
first (then the others they are known in), within the 24-hour window; a
website-chat customer finds it in that chat. Never to a customer who said
STOP, was blocked or erased, nor in the owner's test chats.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deposits import DepositNoticeKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.deposits import DepositRequestDocument
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.shared.proactive_letters import ProactiveLetter, ProactiveSender
from app.use_cases.shared.proactive_routes import ProactiveRouting, RouteChoice
from app.utilities.deposits.deposit_keys import deposit_notice_idempotency_key
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed


@dataclass(frozen=True)
class DepositNotices:
    routing: ProactiveRouting
    sender: ProactiveSender
    contact_repo: ContactRepoContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    suppression_list: SuppressionListContract
    live_events: EventPublisherFacilitatorContract

    def send(
        self,
        business: BusinessDocument,
        request: DepositRequestDocument,
        notice: DepositNoticeKind,
        text: MessageText,
        now: Microseconds,
    ) -> bool:
        """Queue the notice once (its key); False when the customer cannot get it."""

        if request.is_sandbox:
            return False

        contact: ContactDocument | None = self.contact_repo.get(
            business.id, request.contact_id
        )
        if (
            contact is None
            or contact.erased_at is not None
            or is_messaging_suppressed(self.suppression_list, business.id, contact)
        ):
            return False

        letter = ProactiveLetter(
            text=text,
            language=request.language,
            idempotency_key=deposit_notice_idempotency_key(request.id, notice),
            send_before=(
                request.hold_expires_at
                if notice is DepositNoticeKind.REMINDER
                else None
            ),
        )
        choice: RouteChoice = self.routing.choose(
            business, contact, request.source_channel, None, now
        )
        if choice.route is not None:
            conversation_id = self.sender.show(
                business, contact, choice.route, letter, now
            )
            self.sender.queue(business, choice.route, letter, conversation_id, now)
            self._announce(business, conversation_id)
            return True

        return self._show_in_web_chat(business, request, letter, now)

    def _show_in_web_chat(
        self,
        business: BusinessDocument,
        request: DepositRequestDocument,
        letter: ProactiveLetter,
        now: Microseconds,
    ) -> bool:
        if request.source_channel is not ChannelKind.WEB_CHAT or (
            request.conversation_id is None
        ):
            return False

        conversation: ConversationDocument | None = self.conversation_repo.get(
            business.id, request.conversation_id
        )
        if conversation is None or conversation.is_sandbox:
            return False

        self.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=business.id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.STAFF,
                text=letter.text,
                language=letter.language,
                channel=ChannelKind.WEB_CHAT,
                created_at=now,
                updated_at=now,
            )
        )
        self._announce(business, conversation.id)
        return True

    def _announce(
        self, business: BusinessDocument, conversation_id: ConversationId | None
    ) -> None:
        if conversation_id is not None:
            self.live_events.publish(
                business.id, LiveEventKind.CONVERSATION_MESSAGE, (conversation_id,)
            )

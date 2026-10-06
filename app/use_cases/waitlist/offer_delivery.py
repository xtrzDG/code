"""
How an offered place reaches the waiting customer: their messenger first
(where they asked, then the others they are known in), through the outbox
with retries; WhatsApp outside the 24-hour window only with the approved
template (WHATSAPP_WAITLIST_TEMPLATE). A customer who asked in the website
chat and is known in no messenger finds the offer in that chat. The offer
is written into the conversation as the business's message, so the
customer's yes or no (and the assistant) see what was offered.
"""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistOffer
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.use_cases.shared.proactive_letters import ProactiveLetter, ProactiveSender
from app.use_cases.shared.proactive_routes import (
    ProactiveRoute,
    ProactiveRouting,
    RouteChoice,
)
from app.utilities.scheduling.localized_formatting import (
    choose_template_language,
    format_full_date,
    isolate,
)
from app.utilities.scheduling.zoned_time import to_local_moment
from app.utilities.waitlist.waitlist_keys import waitlist_offer_idempotency_key
from app.utilities.waitlist.waitlist_offer_texts import WAITLIST_OFFER_TEXT

MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000


@dataclass(frozen=True)
class OfferPlan:
    """Where the offer goes: a messenger route, or the website chat conversation."""

    contact: ContactDocument
    route: ProactiveRoute | None = None
    web_conversation: ConversationDocument | None = None


@dataclass(frozen=True)
class OfferReceipt:
    """Where the offer went: the channel, its conversation, its outbox message."""

    channel: ChannelKind
    conversation: ConversationDocument | None
    letter: ProactiveLetter
    outbound_message_id: OutboundMessageId | None = None


@dataclass(frozen=True)
class WaitlistOfferDelivery:
    routing: ProactiveRouting
    sender: ProactiveSender
    contact_repo: ContactRepoContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    text_resolver: LocalizedTextResolverContract
    live_events: EventPublisherFacilitatorContract
    whatsapp_template: WhatsAppTemplateName | None

    def plan(
        self,
        business: BusinessDocument,
        entry: WaitlistEntryDocument,
        now: Microseconds,
    ) -> OfferPlan | None:
        """None when the customer cannot be reached now (or is gone or blocked)."""

        contact: ContactDocument | None = self.contact_repo.get(
            business.id, entry.contact_id
        )
        if contact is None or contact.erased_at is not None or contact.block:
            return None

        choice: RouteChoice = self.routing.choose(
            business, contact, entry.source_channel, self.whatsapp_template, now
        )
        if choice.route is not None:
            return OfferPlan(contact=contact, route=choice.route)

        if entry.source_channel is not ChannelKind.WEB_CHAT or (
            entry.conversation_id is None
        ):
            return None

        conversation: ConversationDocument | None = self.conversation_repo.get(
            business.id, entry.conversation_id
        )
        if conversation is None or conversation.is_sandbox:
            return None

        return OfferPlan(contact=contact, web_conversation=conversation)

    def deliver(
        self,
        business: BusinessDocument,
        entry: WaitlistEntryDocument,
        offer: WaitlistOffer,
        plan: OfferPlan,
        zone: ZoneInfo,
    ) -> OfferReceipt:
        letter: ProactiveLetter = self._letter(business, entry, offer, zone)
        now: Microseconds = offer.offered_at
        if plan.route is not None:
            conversation_id = self.sender.show(
                business, plan.contact, plan.route, letter, now
            )
            message_id = self.sender.queue(
                business, plan.route, letter, conversation_id, now
            )
            conversation = (
                None
                if conversation_id is None
                else self.conversation_repo.get(business.id, conversation_id)
            )
            self._announce(business, conversation)
            return OfferReceipt(
                plan.route.identity.channel, conversation, letter, message_id
            )

        conversation = plan.web_conversation
        if conversation is not None:
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
            self._announce(business, conversation)

        return OfferReceipt(ChannelKind.WEB_CHAT, conversation, letter)

    def _announce(
        self, business: BusinessDocument, conversation: ConversationDocument | None
    ) -> None:
        if conversation is not None:
            self.live_events.publish(
                business.id, LiveEventKind.CONVERSATION_MESSAGE, (conversation.id,)
            )

    def _letter(
        self,
        business: BusinessDocument,
        entry: WaitlistEntryDocument,
        offer: WaitlistOffer,
        zone: ZoneInfo,
    ) -> ProactiveLetter:
        language = choose_template_language(WAITLIST_OFFER_TEXT, entry.language)
        starts: datetime = to_local_moment(int(offer.starts_at), zone)
        expires: int = int(entry.offer_expires_at or offer.offered_at)
        minutes: int = max(
            (expires - int(offer.offered_at)) // MICROSECONDS_PER_MINUTE, 1
        )
        values: dict[str, str] = {
            "business": isolate(str(business.name), language),
            "date": format_full_date(starts.date(), language),
            "time": isolate(starts.strftime("%H:%M"), language),
            "minutes": str(minutes),
        }
        template: str = str(self.text_resolver.resolve(WAITLIST_OFFER_TEXT, language))
        return ProactiveLetter(
            text=MessageText(template.format(**values)),
            language=language,
            idempotency_key=waitlist_offer_idempotency_key(
                entry.id, offer.freed_booking_id
            ),
            template_parameters=[
                MessageText(str(business.name)),
                MessageText(values["date"]),
                MessageText(starts.strftime("%H:%M")),
                MessageText(values["minutes"]),
            ],
            send_before=entry.offer_expires_at,
        )

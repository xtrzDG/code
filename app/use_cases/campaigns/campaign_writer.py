"""Writing one campaign message to one customer, or recording why it was not."""

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.schemas.constants.campaigns import (
    CampaignMessageStatus,
    CampaignSkipReason,
    RebookingRuleKind,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import CampaignMessageDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.campaigns.constrained_strings import CampaignMonthKey
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.proactive_letters import ProactiveLetter, ProactiveSender
from app.use_cases.shared.proactive_routes import ProactiveRouting, RouteChoice
from app.utilities.campaigns.campaign_keys import (
    campaign_idempotency_key,
    campaign_message_id_of,
)
from app.utilities.campaigns.campaign_texts import CAMPAIGN_TEXTS, TEMPLATED_RULES
from app.utilities.deliveries.delivery_keys import derive_outbound_message_id
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed
from app.utilities.scheduling.localized_formatting import format_full_date

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
# An invitation the outbox could not deliver within a day is dropped: a
# late "come back" reads as spam.
SEND_WITHIN_SECONDS: int = 24 * 60 * 60


@dataclass(frozen=True)
class CampaignWriter:
    """
    Writes about one booking once: in the customer's messenger and
    language, through the outbox, shown in their conversation. STOP, the
    suppression list and a block always win (SKIPPED, opted out); a
    customer who is gone, unreachable in a connected messenger, or
    reachable only where the 24-hour window is closed without a template
    is skipped with that reason.

    Every message of a campaign (an invitation back, a recall, a
    pre-arrival note) is marketing, so it goes only to a customer whose
    marketing consent is recorded and not taken back (Codice privacy art.
    130(1)-(2); `ContactDocument.marketing_consent`). There is no e-mail
    channel, so the soft opt-in of art. 130(4), which covers e-mail only,
    never applies. A customer without consent gets nothing and nothing is
    stored, so a consent given while the booking is still due counts.
    Service messages (confirmations, reminders, the booking's link) are
    other flows and need no marketing consent.

    The consent's wording promises the messages "in the chat where I made
    this booking", so a message goes only to the customer's identity in
    the booking's own source channel, never to another messenger they are
    known in. A booking made by phone or in the website chat, which cannot
    carry a message the business starts, gets none (NO_CHANNEL).
    """

    message_repo: CampaignMessageRepoContract
    routing: ProactiveRouting
    sender: ProactiveSender
    text_resolver: LocalizedTextResolverContract
    live_events: EventPublisherFacilitatorContract
    suppression_list: SuppressionListContract
    whatsapp_template: WhatsAppTemplateName | None

    def write(
        self,
        business: BusinessDocument,
        rule_kind: RebookingRuleKind,
        booking: BookingDocument,
        contact: ContactDocument | None,
        month: CampaignMonthKey,
        zone: ZoneInfo,
        now: Microseconds,
    ) -> bool:
        """True when a message went out now (it counts against the cap)."""

        message = CampaignMessageDocument(
            id=campaign_message_id_of(business.id, rule_kind, booking.id),
            business_id=business.id,
            contact_id=booking.contact_id,
            rule_kind=rule_kind,
            anchor_booking_id=booking.id,
            status=CampaignMessageStatus.SENT,
            month=month,
            language=booking.language
            or (None if contact is None else contact.language)
            or business.default_language,
            created_at=now,
            updated_at=now,
        )
        if contact is None or contact.erased_at is not None or contact.is_test_only:
            return self._skip(message, CampaignSkipReason.NO_CONTACT)

        if is_messaging_suppressed(self.suppression_list, business.id, contact):
            return self._skip(message, CampaignSkipReason.OPTED_OUT)

        if not contact.has_marketing_consent:
            return False

        choice: RouteChoice = self.routing.choose(
            business,
            in_booking_chat(contact, booking),
            booking.source_channel,
            self.whatsapp_template if rule_kind in TEMPLATED_RULES else None,
            now,
        )
        if choice.route is None:
            return self._skip(
                message,
                CampaignSkipReason.WINDOW_CLOSED
                if choice.is_window_closed
                else CampaignSkipReason.NO_CHANNEL,
            )

        letter: ProactiveLetter = self._letter(business, message, booking, zone, now)
        message.channel = choice.route.identity.channel
        message.sent_at = now
        message.outbound_message_id = derive_outbound_message_id(
            business.id, letter.idempotency_key
        )
        if not self.message_repo.insert_if_new(message):
            return False

        conversation_id = self.sender.show(business, contact, choice.route, letter, now)
        self.sender.queue(business, choice.route, letter, conversation_id, now)
        if conversation_id is not None:

            def link(current: CampaignMessageDocument) -> CampaignMessageDocument:
                current.conversation_id = conversation_id
                current.updated_at = now
                return current

            self.message_repo.update(business.id, message.id, link)
            self.live_events.publish(
                business.id, LiveEventKind.CONVERSATION_MESSAGE, (conversation_id,)
            )

        return True

    def _skip(
        self, message: CampaignMessageDocument, reason: CampaignSkipReason
    ) -> bool:
        message.status = CampaignMessageStatus.SKIPPED
        message.skip_reason = reason
        self.message_repo.insert_if_new(message)
        return False

    def _letter(
        self,
        business: BusinessDocument,
        message: CampaignMessageDocument,
        booking: BookingDocument,
        zone: ZoneInfo,
        now: Microseconds,
    ) -> ProactiveLetter:
        language: LanguageTag = message.language
        starts: datetime = datetime.fromtimestamp(int(booking.starts_at), zone)
        template: str = str(
            self.text_resolver.resolve(CAMPAIGN_TEXTS[message.rule_kind], language)
        )
        text: str = template.format(
            business=str(business.name),
            date=format_full_date(starts.date(), language),
        )
        deadline: int = int(now) + SEND_WITHIN_SECONDS * MICROSECONDS_PER_SECOND
        if message.rule_kind is RebookingRuleKind.PRE_ARRIVAL:
            deadline = min(deadline, int(booking.starts_at) * MICROSECONDS_PER_SECOND)

        return ProactiveLetter(
            text=MessageText(text),
            language=language,
            idempotency_key=campaign_idempotency_key(message.id),
            template_parameters=[MessageText(str(business.name))],
            send_before=Microseconds(deadline),
        )


def in_booking_chat(
    contact: ContactDocument, booking: BookingDocument
) -> ContactDocument:
    """
    The contact as the campaign may reach it: only its identities in the
    channel the booking was made in (the chat its consent names).
    """

    return contact.model_copy(
        update={
            "channel_identities": [
                identity
                for identity in contact.channel_identities
                if identity.channel is booking.source_channel
            ]
        }
    )

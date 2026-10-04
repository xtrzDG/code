"""Deciding and sending the request for feedback after one visit."""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.schemas.constants.feedback import FeedbackRequestStatus, FeedbackSkipReason
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.feedback.request.feedback_limits import (
    FEEDBACK_WINDOW,
    feedback_counters,
    refusal_reason,
)
from app.use_cases.feedback.request.feedback_routes import (
    FeedbackRoute,
    FeedbackRouting,
    feedback_language,
)
from app.use_cases.feedback.request.feedback_sending import (
    FeedbackSender,
    feedback_message_id,
)
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed
from app.utilities.feedback.feedback_keys import (
    feedback_request_id_of,
    new_review_token,
)

MICROSECONDS_PER_SECOND: int = 1_000_000


@dataclass(frozen=True)
class FeedbackAsker:
    """Asks about one visit, or records why it does not (once per visit)."""

    feedback_request_repo: FeedbackRequestRepoContract
    contact_repo: ContactRepoContract
    rate_limits: RequestRateLimitRegistryContract
    routing: FeedbackRouting
    sender: FeedbackSender
    live_events: EventPublisherFacilitatorContract
    suppression_list: SuppressionListContract

    def ask(
        self,
        business: BusinessDocument,
        settings: ReviewSettingsDocument,
        visit: BookingDocument,
        now: Microseconds,
    ) -> bool:
        """True when the customer was asked now."""

        contact: ContactDocument | None = self.contact_repo.get(
            business.id, visit.contact_id
        )
        request = FeedbackRequestDocument(
            id=feedback_request_id_of(business.id, visit.id),
            business_id=business.id,
            booking_id=visit.id,
            contact_id=visit.contact_id,
            visit_ended_at=Microseconds(int(visit.ends_at) * MICROSECONDS_PER_SECOND),
            language=(
                business.default_language
                if contact is None
                else feedback_language(business, contact, visit)
            ),
            status=FeedbackRequestStatus.SENT,
            created_at=now,
            updated_at=now,
        )
        if contact is None or contact.erased_at is not None:
            return self._skip(request, FeedbackSkipReason.NO_CONTACT)

        if is_messaging_suppressed(self.suppression_list, business.id, contact):
            return self._skip(request, FeedbackSkipReason.OPTED_OUT)

        route: FeedbackRoute | FeedbackSkipReason = self.routing.choose(
            business, settings, contact, visit, now
        )
        if isinstance(route, FeedbackSkipReason):
            return self._skip(request, route)

        refused: RateLimitKey | None = self.rate_limits.try_acquire_all(
            feedback_counters(business.id, contact.id), FEEDBACK_WINDOW, now
        )
        if refused is not None:
            return self._skip(request, refusal_reason(business.id, contact.id, refused))

        return self._send(business, contact, request, route, now)

    def _skip(
        self, request: FeedbackRequestDocument, reason: FeedbackSkipReason
    ) -> bool:
        request.status = FeedbackRequestStatus.SKIPPED
        request.skip_reason = reason
        self.feedback_request_repo.insert_if_new(request)
        return False

    def _send(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        request: FeedbackRequestDocument,
        route: FeedbackRoute,
        now: Microseconds,
    ) -> bool:
        text: MessageText = self.sender.request_text(business, request.language)
        request.channel = route.identity.channel
        request.review_token = new_review_token()
        request.outbound_message_id = feedback_message_id(request)
        request.sent_at = now
        if not self.feedback_request_repo.insert_if_new(request):
            return False

        self.sender.queue(business, request, route, text, now)
        conversation_id: ConversationId | None = self.sender.show_in_conversation(
            business, contact, route, text, request.language, now
        )
        if conversation_id is None:
            return True

        def link(current: FeedbackRequestDocument) -> FeedbackRequestDocument:
            current.conversation_id = conversation_id
            current.updated_at = now
            return current

        self.feedback_request_repo.update(business.id, request.id, link)
        self.live_events.publish(
            business.id, LiveEventKind.CONVERSATION_MESSAGE, (conversation_id,)
        )
        return True

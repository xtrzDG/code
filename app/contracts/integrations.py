"""
The public API and outbound webhooks: what reads a business's records in
their public shape, what turns announced changes into webhook deliveries,
and the client that posts a signed delivery to a receiver.
"""

from collections.abc import Sequence
from typing import Protocol

from base_typed_id import BasePrefixedTypedId

from app.contracts.client_contract import ClientContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.integrations.webhook_attempts import (
    WebhookPostRequest,
    WebhookPostResult,
)
from app.schemas.dto.public_api.activity import (
    PublicCall,
    PublicConversation,
    PublicConversationDetail,
    PublicHandoff,
)
from app.schemas.dto.public_api.records import PublicBooking, PublicContact, PublicLead
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.integrations.constrained_strings import WebhookTargetUrl


class PublicRecordReaderContract(FacilitatorContract, Protocol):
    """
    A business's records as the public API and webhooks show them, each
    with the customer it is about and where they came from. None for a
    record of another business or one that is gone.
    """

    def booking(
        self, business: BusinessDocument, booking_id: BookingId
    ) -> PublicBooking | None:
        raise NotImplementedError

    def lead(self, business: BusinessDocument, lead_id: LeadId) -> PublicLead | None:
        raise NotImplementedError

    def contact(
        self, business: BusinessDocument, contact_id: ContactId
    ) -> PublicContact | None:
        raise NotImplementedError

    def conversation(
        self, business: BusinessDocument, conversation_id: ConversationId
    ) -> PublicConversation | None:
        raise NotImplementedError

    def conversation_detail(
        self, business: BusinessDocument, conversation_id: ConversationId
    ) -> PublicConversationDetail | None:
        """The conversation with its latest messages (oldest first)."""
        raise NotImplementedError

    def handoff(
        self, business: BusinessDocument, handoff_id: HandoffId
    ) -> PublicHandoff | None:
        raise NotImplementedError

    def call(self, business: BusinessDocument, call_id: CallId) -> PublicCall | None:
        raise NotImplementedError


class BusinessEventObserverContract(FacilitatorContract, Protocol):
    """
    Hears every change a use case announces through the event publisher
    (`EventPublisherFacilitatorContract`), in the process and the storage
    transaction of the change.
    """

    def notice(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId],
    ) -> None:
        """Never raises: the change is stored whatever the observer does."""
        raise NotImplementedError


class WebhookPosterContract(ClientContract, Protocol):
    """
    Posts a signed webhook to a receiver's public https address, guarded
    against SSRF like every outside address the platform calls: the host
    is resolved and every address it resolves to must be public, the
    connection goes to the vetted address itself (no DNS rebinding), and
    redirects are not followed.
    """

    def post(self, request: WebhookPostRequest) -> WebhookPostResult:
        """Never raises for the receiver's or the network's failures."""
        raise NotImplementedError

    def vet(self, url: WebhookTargetUrl) -> WebhookPostResult | None:
        """
        The checks an address passes before any lookup (https, port 443 or
        80, no credentials, no intranet name or private IP literal): None
        when it passes, else the refusal.
        """
        raise NotImplementedError

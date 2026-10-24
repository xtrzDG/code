"""
The website chat's live stream: signed tickets that let a visitor's widget
listen without its visitor key in the address, and the visitor streams of
an API process.
"""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.live_events import (
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.contracts.utility_contract import UtilityContract
from app.schemas.dto.channels.widget_streams import WidgetStreamClaims
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.compliance.strings import ClientIpAddress


class WidgetStreamTicketSignerContract(UtilityContract, Protocol):
    def sign(self, claims: WidgetStreamClaims) -> WidgetStreamTicket:
        """A compact ticket that carries the claims and their signature."""
        raise NotImplementedError

    def read(self, ticket: WidgetStreamTicket) -> WidgetStreamClaims | None:
        """
        The claims of a ticket this platform signed; None for a forged,
        altered or malformed one. Expiry is the caller's check.
        """
        raise NotImplementedError


class WidgetEventStreamFacilitatorContract(FacilitatorContract, Protocol):
    def open(
        self,
        business_id: BusinessId,
        visitor_id: WidgetVisitorId,
        client_ip_address: ClientIpAddress | None,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        """
        Hand the visitor's own widget events (typing, replies) of the
        business to `subscriber` until the subscription is cancelled (which
        gives the stream's place back; idempotent). Raises RateLimitedError
        when the business or the client network already has the most
        visitor streams open on this process.
        """
        raise NotImplementedError

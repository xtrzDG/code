"""
Who calls the public API (a business's API key) and the inputs of its
operations: each names the key's business, so its operator runs in that
business's storage scope and no other.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.integrations.constrained_integers import (
    PublicApiRequestsPerMinute,
)
from app.schemas.typings.integrations.constrained_strings import (
    ApiKeyName,
    ApiKeyToken,
)
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId


class ApiKeyCredentials(ImmutableDTO):
    """The bearer token a request carried and where it came from."""

    token: ApiKeyToken
    client_ip_address: ClientIpAddress | None = None


class ApiKeyPrincipal(ImmutableDTO):
    """
    An authenticated key: its business, what it may do, and the owner who
    made it (the actor of the changes it makes and the user its
    Idempotency-Keys belong to).
    """

    api_key_id: ApiKeyId
    api_key_name: ApiKeyName
    business_id: BusinessId
    scopes: list[ApiKeyScope]
    created_by: UserId
    client_ip_address: ClientIpAddress | None = None


class PublicApiCall(ImmutableDTO):
    """An operation of the public API on behalf of a key."""

    principal: ApiKeyPrincipal

    @property
    def business_id(self) -> BusinessId:
        """The key's business: the only one the operation may touch."""

        return self.principal.business_id


class PublicApiIdentity(ImmutableDTO):
    """`GET /v1/public-api/me`: the key, its business and its limits."""

    business_id: BusinessId
    business_name: BusinessName
    api_key_id: ApiKeyId
    api_key_name: ApiKeyName
    scopes: list[ApiKeyScope]
    requests_per_minute: PublicApiRequestsPerMinute


class PublicListQuery(PublicApiCall):
    page: PageRequest


class PublicBookingQuery(PublicApiCall):
    booking_id: BookingId


class PublicLeadQuery(PublicApiCall):
    lead_id: LeadId


class PublicContactQuery(PublicApiCall):
    contact_id: ContactId


class PublicConversationQuery(PublicApiCall):
    conversation_id: ConversationId

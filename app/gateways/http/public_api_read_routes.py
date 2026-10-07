"""
The stable public API, reads: `/v1/public-api/*` with an API key
(`Authorization: Bearer awk_…`). A frozen contract (docs/api-versioning.md):
fields are only ever added.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.api_key_authentication import ApiKeyAuthentication
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import parse_path_identifier
from app.schemas.dto.public_api.access import (
    ApiKeyPrincipal,
    PublicApiCall,
    PublicApiIdentity,
    PublicBookingQuery,
    PublicContactQuery,
    PublicConversationQuery,
    PublicLeadQuery,
    PublicListQuery,
)
from app.schemas.dto.public_api.activity import PublicConversationDetail
from app.schemas.dto.public_api.pages import (
    PublicBookingPage,
    PublicContactPage,
    PublicConversationPage,
    PublicLeadPage,
)
from app.schemas.dto.public_api.records import PublicBooking, PublicContact, PublicLead
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId

PUBLIC_API_PATH: str = "/v1/public-api"
PUBLIC_API_TAG: str = "public-api"

type PageOperator[Page] = OperatorContract[PublicListQuery, Page]


def build_public_api_read_router(
    *,
    api_key: ApiKeyAuthentication,
    get_identity: OperatorContract[PublicApiCall, PublicApiIdentity],
    list_bookings: PageOperator[PublicBookingPage],
    get_booking: OperatorContract[PublicBookingQuery, PublicBooking],
    list_leads: PageOperator[PublicLeadPage],
    get_lead: OperatorContract[PublicLeadQuery, PublicLead],
    list_contacts: PageOperator[PublicContactPage],
    get_contact: OperatorContract[PublicContactQuery, PublicContact],
    list_conversations: PageOperator[PublicConversationPage],
    get_conversation: OperatorContract[
        PublicConversationQuery, PublicConversationDetail
    ],
) -> APIRouter:
    """
    Reads of the key's business (each needs its `<records>:read` scope; a
    record of another business is 404):
        GET /v1/public-api/me                       the key and its business
        GET /v1/public-api/bookings[/{id}]          ?limit&cursor
        GET /v1/public-api/leads[/{id}]
        GET /v1/public-api/contacts[/{id}]
        GET /v1/public-api/conversations[/{id}]     one with its messages
    """

    router = APIRouter(tags=[PUBLIC_API_TAG], responses=standard_error_responses())

    def page_of(
        principal: ApiKeyPrincipal, limit: str | None, cursor: str | None
    ) -> PublicListQuery:
        return PublicListQuery(
            principal=principal, page=parse_page_request(limit, cursor)
        )

    @router.get(f"{PUBLIC_API_PATH}/me")
    def get_me(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
    ) -> PublicApiIdentity:
        return get_identity.operate(PublicApiCall(principal=principal))

    @router.get(f"{PUBLIC_API_PATH}/bookings")
    def list_bookings_page(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> PublicBookingPage:
        return list_bookings.operate(page_of(principal, limit, cursor))

    @router.get(f"{PUBLIC_API_PATH}/bookings/{{booking_id}}")
    def get_booking_record(
        booking_id: str, principal: Annotated[ApiKeyPrincipal, Depends(api_key)]
    ) -> PublicBooking:
        return get_booking.operate(
            PublicBookingQuery(
                principal=principal,
                booking_id=parse_path_identifier(booking_id, BookingId, "Booking"),
            )
        )

    @router.get(f"{PUBLIC_API_PATH}/leads")
    def list_leads_page(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> PublicLeadPage:
        return list_leads.operate(page_of(principal, limit, cursor))

    @router.get(f"{PUBLIC_API_PATH}/leads/{{lead_id}}")
    def get_lead_record(
        lead_id: str, principal: Annotated[ApiKeyPrincipal, Depends(api_key)]
    ) -> PublicLead:
        return get_lead.operate(
            PublicLeadQuery(
                principal=principal,
                lead_id=parse_path_identifier(lead_id, LeadId, "Lead"),
            )
        )

    @router.get(f"{PUBLIC_API_PATH}/contacts")
    def list_contacts_page(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> PublicContactPage:
        return list_contacts.operate(page_of(principal, limit, cursor))

    @router.get(f"{PUBLIC_API_PATH}/contacts/{{contact_id}}")
    def get_contact_record(
        contact_id: str, principal: Annotated[ApiKeyPrincipal, Depends(api_key)]
    ) -> PublicContact:
        return get_contact.operate(
            PublicContactQuery(
                principal=principal,
                contact_id=parse_path_identifier(contact_id, ContactId, "Contact"),
            )
        )

    @router.get(f"{PUBLIC_API_PATH}/conversations")
    def list_conversations_page(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> PublicConversationPage:
        return list_conversations.operate(page_of(principal, limit, cursor))

    @router.get(f"{PUBLIC_API_PATH}/conversations/{{conversation_id}}")
    def get_conversation_record(
        conversation_id: str, principal: Annotated[ApiKeyPrincipal, Depends(api_key)]
    ) -> PublicConversationDetail:
        return get_conversation.operate(
            PublicConversationQuery(
                principal=principal,
                conversation_id=parse_path_identifier(
                    conversation_id, ConversationId, "Conversation"
                ),
            )
        )

    return router

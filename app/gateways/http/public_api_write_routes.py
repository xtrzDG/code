"""
The stable public API, writes: bookings and leads made through an API
key, and REST-hook subscriptions (Zapier). Creating routes take an
`Idempotency-Key` (kept 24 hours per key owner).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.api_key_authentication import ApiKeyAuthentication
from app.gateways.http.idempotency.idempotency_dependency import (
    NO_IDEMPOTENCY,
    IdempotencyDependency,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.public_api_read_routes import PUBLIC_API_PATH, PUBLIC_API_TAG
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.schemas.dto.integrations.webhook_views import CreatedWebhookEndpoint
from app.schemas.dto.public_api.access import ApiKeyPrincipal
from app.schemas.dto.public_api.commands import (
    PublicBookingCommand,
    PublicBookingRequest,
    PublicLeadCommand,
    PublicLeadRequest,
    PublicWebhookCommand,
    PublicWebhookRemoval,
    PublicWebhookRequest,
)
from app.schemas.dto.public_api.records import PublicBooking, PublicLead
from app.schemas.typings.integrations.prefixed_id import WebhookEndpointId

read_booking_body = build_json_body_dependency(PublicBookingRequest)
read_lead_body = build_json_body_dependency(PublicLeadRequest)
read_webhook_body = build_json_body_dependency(PublicWebhookRequest)


def build_public_api_write_router(
    *,
    api_key: ApiKeyAuthentication,
    create_booking: OperatorContract[PublicBookingCommand, PublicBooking],
    create_lead: OperatorContract[PublicLeadCommand, PublicLead],
    subscribe_webhook: OperatorContract[PublicWebhookCommand, CreatedWebhookEndpoint],
    unsubscribe_webhook: OperatorContract[PublicWebhookRemoval, None],
    idempotent: IdempotencyDependency = NO_IDEMPOTENCY,
) -> APIRouter:
    """
    Writes of the key's business:
        POST   /v1/public-api/bookings        `bookings:write` (201)
        POST   /v1/public-api/leads           `leads:write` (201)
        POST   /v1/public-api/webhooks        `webhooks:manage`: subscribe a
                                              URL to events, the signing
                                              secret once (201)
        DELETE /v1/public-api/webhooks/{id}   unsubscribe (204)
    """

    router = APIRouter(tags=[PUBLIC_API_TAG], responses=standard_error_responses())

    @router.post(
        f"{PUBLIC_API_PATH}/bookings",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(idempotent)],
        openapi_extra=describe_json_body(PublicBookingRequest),
    )
    def create_booking_record(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
        body: Annotated[PublicBookingRequest, Depends(read_booking_body)],
    ) -> PublicBooking:
        return create_booking.operate(
            PublicBookingCommand(principal=principal, request=body)
        )

    @router.post(
        f"{PUBLIC_API_PATH}/leads",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(idempotent)],
        openapi_extra=describe_json_body(PublicLeadRequest),
    )
    def create_lead_record(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
        body: Annotated[PublicLeadRequest, Depends(read_lead_body)],
    ) -> PublicLead:
        return create_lead.operate(PublicLeadCommand(principal=principal, request=body))

    @router.post(
        f"{PUBLIC_API_PATH}/webhooks",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(idempotent)],
        openapi_extra=describe_json_body(PublicWebhookRequest),
    )
    def subscribe_webhook_url(
        principal: Annotated[ApiKeyPrincipal, Depends(api_key)],
        body: Annotated[PublicWebhookRequest, Depends(read_webhook_body)],
    ) -> CreatedWebhookEndpoint:
        return subscribe_webhook.operate(
            PublicWebhookCommand(principal=principal, request=body)
        )

    @router.delete(
        f"{PUBLIC_API_PATH}/webhooks/{{webhook_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def unsubscribe_webhook_url(
        webhook_id: str, principal: Annotated[ApiKeyPrincipal, Depends(api_key)]
    ) -> None:
        unsubscribe_webhook.operate(
            PublicWebhookRemoval(
                principal=principal,
                endpoint_id=parse_path_identifier(
                    webhook_id, WebhookEndpointId, "Webhook"
                ),
            )
        )

    return router

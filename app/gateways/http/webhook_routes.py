"""Settings → Integrations → Webhooks (cabinet, bearer token, owners only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.integrations.webhook_views import (
    CreatedWebhookEndpoint,
    CreateWebhookEndpointCommand,
    UpdateWebhookEndpointCommand,
    WebhookDeliveriesQuery,
    WebhookDeliveryCommand,
    WebhookDeliveryDetail,
    WebhookDeliveryPage,
    WebhookDeliveryView,
    WebhookEndpointChange,
    WebhookEndpointCommand,
    WebhookEndpointList,
    WebhookEndpointRequest,
    WebhookEndpointsQuery,
    WebhookEndpointView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.prefixed_id import (
    WebhookDeliveryId,
    WebhookEndpointId,
)
from app.schemas.typings.users.prefixed_id import UserId

WEBHOOKS_PATH: str = "/v1/businesses/{business_id}/webhooks"
ENDPOINT_PATH: str = f"{WEBHOOKS_PATH}/{{webhook_id}}"
DELIVERY_PATH: str = "/v1/businesses/{business_id}/webhook-deliveries/{delivery_id}"

read_endpoint_body = build_json_body_dependency(WebhookEndpointRequest)
read_change_body = build_json_body_dependency(WebhookEndpointChange)

type EndpointOperator[Output] = OperatorContract[WebhookEndpointCommand, Output]
type DeliveryOperator[Output] = OperatorContract[WebhookDeliveryCommand, Output]


def build_webhook_router(
    *,
    current_user: CurrentUserDependency,
    list_endpoints: OperatorContract[WebhookEndpointsQuery, WebhookEndpointList],
    create_endpoint: OperatorContract[
        CreateWebhookEndpointCommand, CreatedWebhookEndpoint
    ],
    update_endpoint: OperatorContract[
        UpdateWebhookEndpointCommand, WebhookEndpointView
    ],
    rotate_secret: EndpointOperator[CreatedWebhookEndpoint],
    delete_endpoint: EndpointOperator[None],
    send_test: EndpointOperator[WebhookDeliveryView],
    list_deliveries: OperatorContract[WebhookDeliveriesQuery, WebhookDeliveryPage],
    get_delivery: DeliveryOperator[WebhookDeliveryDetail],
    retry_delivery: DeliveryOperator[WebhookDeliveryView],
) -> APIRouter:
    """
    Routes of the business's outbound webhooks (owners; staff get 403):
        GET    .../webhooks                       endpoints and the event catalog
        POST   .../webhooks                       {url, label?, event_types} (201;
                                                  the signing secret, shown once)
        PATCH  .../webhooks/{id}                  url, label, events, pause/resume
        POST   .../webhooks/{id}/rotate-secret    a new secret, shown once
        DELETE .../webhooks/{id}                  204
        POST   .../webhooks/{id}/test             "Send test event": one signed
                                                  POST now, its delivery
        GET    .../webhooks/{id}/deliveries       the delivery log, newest first
        GET    .../webhook-deliveries/{id}        one delivery with its payload
        POST   .../webhook-deliveries/{id}/retry  queue a failed delivery again
    """

    router = APIRouter(tags=["webhooks"], responses=standard_error_responses())

    def endpoint_command(
        user_id: UserId, business_id: str, webhook_id: str, request: Request
    ) -> WebhookEndpointCommand:
        return WebhookEndpointCommand(
            user_id=user_id,
            business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            endpoint_id=parse_path_identifier(webhook_id, WebhookEndpointId, "Webhook"),
            client_ip_address=read_client_ip_address(request),
        )

    def delivery_command(
        user_id: UserId, business_id: str, delivery_id: str, request: Request
    ) -> WebhookDeliveryCommand:
        return WebhookDeliveryCommand(
            user_id=user_id,
            business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            delivery_id=parse_path_identifier(
                delivery_id, WebhookDeliveryId, "Webhook delivery"
            ),
            client_ip_address=read_client_ip_address(request),
        )

    @router.get(WEBHOOKS_PATH)
    def list_webhooks(
        business_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> WebhookEndpointList:
        return list_endpoints.operate(
            WebhookEndpointsQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.post(
        WEBHOOKS_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(WebhookEndpointRequest),
    )
    def create_webhook(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[WebhookEndpointRequest, Depends(read_endpoint_body)],
    ) -> CreatedWebhookEndpoint:
        return create_endpoint.operate(
            CreateWebhookEndpointCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.patch(
        ENDPOINT_PATH, openapi_extra=describe_json_body(WebhookEndpointChange)
    )
    def update_webhook(
        business_id: str,
        webhook_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[WebhookEndpointChange, Depends(read_change_body)],
    ) -> WebhookEndpointView:
        command = endpoint_command(user_id, business_id, webhook_id, request)
        return update_endpoint.operate(
            UpdateWebhookEndpointCommand(**command.model_dump(), change=body)
        )

    @router.post(f"{ENDPOINT_PATH}/rotate-secret")
    def rotate_webhook_secret(
        business_id: str,
        webhook_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CreatedWebhookEndpoint:
        return rotate_secret.operate(
            endpoint_command(user_id, business_id, webhook_id, request)
        )

    @router.delete(ENDPOINT_PATH, status_code=status.HTTP_204_NO_CONTENT)
    def delete_webhook(
        business_id: str,
        webhook_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        delete_endpoint.operate(
            endpoint_command(user_id, business_id, webhook_id, request)
        )

    @router.post(f"{ENDPOINT_PATH}/test")
    def send_webhook_test(
        business_id: str,
        webhook_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> WebhookDeliveryView:
        return send_test.operate(
            endpoint_command(user_id, business_id, webhook_id, request)
        )

    @router.get(f"{ENDPOINT_PATH}/deliveries")
    def list_webhook_deliveries(
        business_id: str,
        webhook_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> WebhookDeliveryPage:
        command = endpoint_command(user_id, business_id, webhook_id, request)
        return list_deliveries.operate(
            WebhookDeliveriesQuery(
                user_id=user_id,
                business_id=command.business_id,
                endpoint_id=command.endpoint_id,
                page=parse_page_request(limit, cursor),
            )
        )

    @router.get(DELIVERY_PATH)
    def get_webhook_delivery(
        business_id: str,
        delivery_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> WebhookDeliveryDetail:
        return get_delivery.operate(
            delivery_command(user_id, business_id, delivery_id, request)
        )

    @router.post(f"{DELIVERY_PATH}/retry")
    def retry_webhook_delivery(
        business_id: str,
        delivery_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> WebhookDeliveryView:
        return retry_delivery.operate(
            delivery_command(user_id, business_id, delivery_id, request)
        )

    return router

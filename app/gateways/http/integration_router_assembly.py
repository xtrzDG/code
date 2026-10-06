"""
Routers of the integrations (1181): the cabinet's webhooks and API keys,
and the public API that the keys open.
"""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.api_key_authentication import build_api_key_authentication
from app.gateways.http.api_key_routes import build_api_key_router
from app.gateways.http.idempotency.idempotency_dependency import (
    build_idempotency_dependency,
)
from app.gateways.http.public_api_read_routes import build_public_api_read_router
from app.gateways.http.public_api_write_routes import build_public_api_write_router
from app.gateways.http.user_authentication import CurrentUserDependency
from app.gateways.http.webhook_routes import build_webhook_router


def build_integration_routers(
    operators: OperatorsContainer, current_user: CurrentUserDependency
) -> list[APIRouter]:
    """Settings → Integrations (webhooks, API keys) and /v1/public-api/*."""

    webhooks = operators.webhooks
    public_api = operators.public_api
    api_key, key_owner = build_api_key_authentication(
        public_api.authenticate_api_key_operator(),
        operators.spend_guard.admit_api_request_operator(),
    )
    return [
        build_webhook_router(
            current_user=current_user,
            list_endpoints=webhooks.list_webhook_endpoints_operator(),
            create_endpoint=webhooks.create_webhook_endpoint_operator(),
            update_endpoint=webhooks.update_webhook_endpoint_operator(),
            rotate_secret=webhooks.rotate_webhook_secret_operator(),
            delete_endpoint=webhooks.delete_webhook_endpoint_operator(),
            send_test=webhooks.send_webhook_test_operator(),
            list_deliveries=webhooks.list_webhook_deliveries_operator(),
            get_delivery=webhooks.get_webhook_delivery_operator(),
            retry_delivery=webhooks.retry_webhook_delivery_operator(),
        ),
        build_api_key_router(
            current_user=current_user,
            list_api_keys=public_api.list_api_keys_operator(),
            create_api_key=public_api.create_api_key_operator(),
            revoke_api_key=public_api.revoke_api_key_operator(),
        ),
        build_public_api_read_router(
            api_key=api_key,
            get_identity=public_api.get_public_identity_operator(),
            list_bookings=public_api.list_public_bookings_operator(),
            get_booking=public_api.get_public_booking_operator(),
            list_leads=public_api.list_public_leads_operator(),
            get_lead=public_api.get_public_lead_operator(),
            list_contacts=public_api.list_public_contacts_operator(),
            get_contact=public_api.get_public_contact_operator(),
            list_conversations=public_api.list_public_conversations_operator(),
            get_conversation=public_api.get_public_conversation_operator(),
        ),
        build_public_api_write_router(
            api_key=api_key,
            create_booking=public_api.create_public_booking_operator(),
            create_lead=public_api.create_public_lead_operator(),
            subscribe_webhook=public_api.subscribe_public_webhook_operator(),
            unsubscribe_webhook=public_api.unsubscribe_public_webhook_operator(),
            idempotent=build_idempotency_dependency(
                key_owner,
                operators.idempotency.claim_idempotency_key_operator(),
                operators.idempotency.finish_idempotent_request_operator(),
            ),
        ),
    ]

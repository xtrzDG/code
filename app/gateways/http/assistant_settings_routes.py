"""Settings → General: how the assistant remembers returning customers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.customer_memory.assistant_settings import (
    AssistantSettingsCommand,
    AssistantSettingsQuery,
    AssistantSettingsRequest,
    AssistantSettingsView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_settings_body = build_json_body_dependency(AssistantSettingsRequest)
SETTINGS_PATH: str = "/v1/businesses/{business_id}/assistant-settings"


def build_assistant_settings_router(
    current_user: CurrentUserDependency,
    get_assistant_settings_operator: OperatorContract[
        AssistantSettingsQuery, AssistantSettingsView
    ],
    update_assistant_settings_operator: OperatorContract[
        AssistantSettingsCommand, AssistantSettingsView
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token):
        GET  /v1/businesses/{business_id}/assistant-settings
                                    whether the assistant remembers returning
                                    customers and reads the team's notes on
                                    them (owners and staff)
        PUT  /v1/businesses/{business_id}/assistant-settings
                                    {remembers_customers, shares_team_notes}
                                    (owners; audited)
    """

    router = APIRouter(
        tags=["assistant settings"], responses=standard_error_responses()
    )

    @router.get(SETTINGS_PATH)
    def get_assistant_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AssistantSettingsView:
        return get_assistant_settings_operator.operate(
            AssistantSettingsQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.put(
        SETTINGS_PATH, openapi_extra=describe_json_body(AssistantSettingsRequest)
    )
    def update_assistant_settings(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AssistantSettingsRequest, Depends(read_settings_body)],
    ) -> AssistantSettingsView:
        return update_assistant_settings_operator.operate(
            AssistantSettingsCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                settings=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router

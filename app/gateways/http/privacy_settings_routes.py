"""Cabinet Settings → Privacy: how long customers' data is kept."""

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
from app.schemas.dto.retention import (
    PrivacySettingsQuery,
    PrivacySettingsRequest,
    PrivacySettingsView,
    UpdatePrivacySettingsCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

B: str = "/v1/businesses/{business_id}"

read_privacy_settings_body = build_json_body_dependency(PrivacySettingsRequest)


def build_privacy_settings_router(
    *,
    current_user: CurrentUserDependency,
    get_settings: OperatorContract[PrivacySettingsQuery, PrivacySettingsView],
    update_settings: OperatorContract[
        UpdatePrivacySettingsCommand, PrivacySettingsView
    ],
) -> APIRouter:
    """
    Routes (Bearer auth; owners):
        GET {B}/privacy-settings       retention periods and the latest purge
        PUT {B}/privacy-settings       change the periods (a shorter one asks
                                       for a recent sign-in)
    """

    router = APIRouter(tags=["compliance"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    @router.get(f"{B}/privacy-settings")
    def get_privacy_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PrivacySettingsView:
        return get_settings.operate(
            PrivacySettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/privacy-settings",
        openapi_extra=describe_json_body(PrivacySettingsRequest),
    )
    def update_privacy_settings(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PrivacySettingsRequest, Depends(read_privacy_settings_body)],
    ) -> PrivacySettingsView:
        return update_settings.operate(
            UpdatePrivacySettingsCommand(
                user_id=user_id,
                business_id=business(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router

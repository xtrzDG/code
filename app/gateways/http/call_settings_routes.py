"""Cabinet Settings → Calls: summaries, text-backs and the latest text-backs."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

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
from app.schemas.dto.calls.call_settings import (
    CallSettingsQuery,
    CallSettingsRequest,
    CallSettingsView,
    TextBackPage,
    TextBackPageQuery,
    UpdateCallSettingsCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

B: str = "/v1/businesses/{business_id}"

read_call_settings_body = build_json_body_dependency(CallSettingsRequest)


def build_call_settings_router(
    *,
    current_user: CurrentUserDependency,
    get_settings: OperatorContract[CallSettingsQuery, CallSettingsView],
    update_settings: OperatorContract[UpdateCallSettingsCommand, CallSettingsView],
    list_text_backs: OperatorContract[TextBackPageQuery, TextBackPage],
) -> APIRouter:
    """
    Routes (Bearer auth; owners):
        GET {B}/call-settings          summaries, text-backs, template previews
        PUT {B}/call-settings          change them
        GET {B}/text-backs             callers who did not get through (paged)
    """

    router = APIRouter(tags=["calls"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    @router.get(f"{B}/call-settings")
    def get_call_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CallSettingsView:
        return get_settings.operate(
            CallSettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/call-settings",
        openapi_extra=describe_json_body(CallSettingsRequest),
    )
    def update_call_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CallSettingsRequest, Depends(read_call_settings_body)],
    ) -> CallSettingsView:
        return update_settings.operate(
            UpdateCallSettingsCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.get(f"{B}/text-backs")
    def list_call_text_backs(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: Annotated[str | None, Query()] = None,
        cursor: Annotated[str | None, Query()] = None,
    ) -> TextBackPage:
        return list_text_backs.operate(
            TextBackPageQuery(
                user_id=user_id,
                business_id=business(business_id),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router

"""Cabinet Channels → Website chat: the websites allowed to show it."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.widget_origins import (
    SaveWidgetAllowedOriginsCommand,
    WidgetAllowedOriginsQuery,
    WidgetAllowedOriginsRequest,
    WidgetAllowedOriginsView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

ALLOWED_ORIGINS_PATH: str = "/v1/businesses/{business_id}/channels/web/allowed-origins"

read_allowed_origins_body = build_json_body_dependency(WidgetAllowedOriginsRequest)


def build_widget_origin_router(
    *,
    current_user: CurrentUserDependency,
    get_allowed_origins: OperatorContract[
        WidgetAllowedOriginsQuery, WidgetAllowedOriginsView
    ],
    save_allowed_origins: OperatorContract[
        SaveWidgetAllowedOriginsCommand, WidgetAllowedOriginsView
    ],
) -> APIRouter:
    """
    Routes (Bearer auth):
        GET {path}    the websites allowed to show the chat (team members)
        PUT {path}    set them (owners): addresses become origins, one per
                      site; an empty list lets any website show the chat.
                      The hosted chat page and the cabinet's preview always
                      may. A foreign website's widget requests get 403.
    """

    router = APIRouter(tags=["channels"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    @router.get(ALLOWED_ORIGINS_PATH)
    def get_widget_allowed_origins(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> WidgetAllowedOriginsView:
        return get_allowed_origins.operate(
            WidgetAllowedOriginsQuery(
                user_id=user_id, business_id=business(business_id)
            )
        )

    @router.put(
        ALLOWED_ORIGINS_PATH,
        openapi_extra=describe_json_body(WidgetAllowedOriginsRequest),
    )
    def save_widget_allowed_origins(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            WidgetAllowedOriginsRequest, Depends(read_allowed_origins_body)
        ],
    ) -> WidgetAllowedOriginsView:
        return save_allowed_origins.operate(
            SaveWidgetAllowedOriginsCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    return router

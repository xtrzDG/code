"""Knowledge import from the business's own website (cabinet)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.errors import ErrorBody
from app.schemas.dto.website_import import (
    CurrentWebsiteImport,
    GetWebsiteImportQuery,
    StartWebsiteImportCommand,
    WebsiteImportRequest,
    WebsiteImportView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_website_import_body = build_json_body_dependency(WebsiteImportRequest)
START_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorBody,
        "description": (
            "The business's last website import is still reading its site "
            "(reasons[].code website_import_running)."
        ),
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorBody,
        "description": (
            "The address cannot be read: reasons[].code website_link_invalid "
            "with details not_http, credentials_in_url, port_not_allowed or "
            "not_public (only public http(s) addresses on ports 80 and 443)."
        ),
    },
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorBody,
        "description": (
            "The business started 10 website imports in the last hour "
            "(Retry-After says when the next one is allowed)."
        ),
    },
}


def build_website_import_router(
    start_website_import_operator: OperatorContract[
        StartWebsiteImportCommand, WebsiteImportView
    ],
    get_website_import_operator: OperatorContract[
        GetWebsiteImportQuery, CurrentWebsiteImport
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token; owners and staff):
        POST /v1/businesses/{business_id}/knowledge/import-website {url}
                 queue the reading of the site (202): its import id and
                 status; progress arrives as knowledge_import.progress live
                 events
        GET  /v1/businesses/{business_id}/knowledge/import-website/current
                 the current import, with its drafts once it is done
    """

    router = APIRouter(tags=["knowledge"], responses=standard_error_responses())

    @router.post(
        "/v1/businesses/{business_id}/knowledge/import-website",
        status_code=status.HTTP_202_ACCEPTED,
        openapi_extra=describe_json_body(WebsiteImportRequest),
        responses=START_RESPONSES,
    )
    def start_website_import(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[WebsiteImportRequest, Depends(read_website_import_body)],
    ) -> WebsiteImportView:
        return start_website_import_operator.operate(
            StartWebsiteImportCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                url=body.url,
            )
        )

    # Not .../knowledge/import-website itself: GET .../knowledge/{item_id}
    # would take that path for a knowledge item.
    @router.get("/v1/businesses/{business_id}/knowledge/import-website/current")
    def get_website_import(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CurrentWebsiteImport:
        return get_website_import_operator.operate(
            GetWebsiteImportQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    return router

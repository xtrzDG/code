"""Sharing the assistant: the hosted chat page's address and channel links."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.sharing import (
    PublicSlugCommand,
    PublicSlugRequest,
    ShareLinksQuery,
    ShareLinksView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.sharing.constrained_strings import ShareSourceTag
from app.schemas.typings.users.prefixed_id import UserId

SHARE_LINKS_PATH: str = "/v1/businesses/{business_id}/share-links"
PUBLIC_SLUG_PATH: str = "/v1/businesses/{business_id}/public-slug"

read_public_slug_body = build_json_body_dependency(PublicSlugRequest)


def build_sharing_router(
    current_user: CurrentUserDependency,
    get_share_links_operator: OperatorContract[ShareLinksQuery, ShareLinksView],
    set_public_slug_operator: OperatorContract[PublicSlugCommand, ShareLinksView],
) -> APIRouter:
    """
    Routes (bearer token; reads for owners and staff, the address for
    owners):
        GET /v1/businesses/{business_id}/share-links?src=<tag>
            the hosted chat page (/c/{slug} on the cabinet's site) and a
            link per channel that is switched on, tagged with where they
            will be put (?src= on the hosted page, ?ref= on m.me and
            ig.me); the first call gives the business its address
        PUT /v1/businesses/{business_id}/public-slug
            a new address for the hosted chat page (409 slug_taken,
            422 slug_reserved); old addresses keep leading to the business
    """

    router: APIRouter = APIRouter(
        tags=["sharing"], responses=standard_error_responses()
    )

    @router.get(SHARE_LINKS_PATH)
    def get_share_links(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        src: Annotated[str | None, Query()] = None,
    ) -> ShareLinksView:
        return get_share_links_operator.operate(
            ShareLinksQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                source=parse_optional(src, ShareSourceTag, "src"),
            )
        )

    @router.put(PUBLIC_SLUG_PATH, openapi_extra=describe_json_body(PublicSlugRequest))
    def set_public_slug(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PublicSlugRequest, Depends(read_public_slug_body)],
    ) -> ShareLinksView:
        return set_public_slug_operator.operate(
            PublicSlugCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
            )
        )

    return router

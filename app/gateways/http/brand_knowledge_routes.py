"""
The knowledge a brand's locations share, and a location's own ways with its
brand: replacing a shared fact, leaving the brand (cabinet, bearer token).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.brand_routes import BRAND_PATH, brand_of
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.brands.brand_commands import BrandQuery, LeaveBrandCommand
from app.schemas.dto.brands.brand_knowledge import (
    BrandKnowledgeCommand,
    BrandKnowledgeItemCommand,
    BrandKnowledgeItemRequest,
    BrandKnowledgeItemView,
    BrandKnowledgeList,
    OverrideBrandKnowledgeCommand,
    OverrideBrandKnowledgeRequest,
)
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.users.prefixed_id import UserId

ITEM_PATH: str = f"{BRAND_PATH}/knowledge/{{shared_key}}"
LOCATION_PATH: str = "/v1/businesses/{business_id}"
read_item_body = build_json_body_dependency(BrandKnowledgeItemRequest)
read_override_body = build_json_body_dependency(OverrideBrandKnowledgeRequest)


def build_brand_knowledge_router(
    *,
    current_user: CurrentUserDependency,
    list_items: OperatorContract[BrandQuery, BrandKnowledgeList],
    create_item: OperatorContract[BrandKnowledgeCommand, BrandKnowledgeItemView],
    update_item: OperatorContract[BrandKnowledgeItemCommand, BrandKnowledgeItemView],
    delete_item: OperatorContract[BrandKnowledgeItemCommand, None],
    override_item: OperatorContract[
        OverrideBrandKnowledgeCommand, KnowledgeItemDetails
    ],
    leave_brand: OperatorContract[LeaveBrandCommand, None],
) -> APIRouter:
    """
    Routes:
        GET    {B}/knowledge                    members: the shared facts
        POST   {B}/knowledge                    brand owners: share a fact
        PUT    {B}/knowledge/{shared_key}       brand owners: change it
        DELETE {B}/knowledge/{shared_key}       brand owners: stop sharing it
        POST   /v1/businesses/{id}/knowledge/brand-overrides
                                                the location's own copy of a
                                                shared fact (owners and staff)
        DELETE /v1/businesses/{id}/brand        owners: leave the brand
    """

    router = APIRouter(tags=["brands"], responses=standard_error_responses())

    def key_of(raw_key: str) -> KnowledgeShareKey:
        return parse_path_identifier(raw_key, KnowledgeShareKey, "Shared item")

    @router.get(f"{BRAND_PATH}/knowledge")
    def list_brand_knowledge(
        brand_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> BrandKnowledgeList:
        return list_items.operate(
            BrandQuery(user_id=user_id, brand_id=brand_of(brand_id))
        )

    @router.post(
        f"{BRAND_PATH}/knowledge",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(BrandKnowledgeItemRequest),
    )
    def create_brand_knowledge_item(
        brand_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[BrandKnowledgeItemRequest, Depends(read_item_body)],
    ) -> BrandKnowledgeItemView:
        return create_item.operate(
            BrandKnowledgeCommand(
                user_id=user_id, brand_id=brand_of(brand_id), request=body
            )
        )

    @router.put(ITEM_PATH, openapi_extra=describe_json_body(BrandKnowledgeItemRequest))
    def update_brand_knowledge_item(
        brand_id: str,
        shared_key: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[BrandKnowledgeItemRequest, Depends(read_item_body)],
    ) -> BrandKnowledgeItemView:
        return update_item.operate(
            BrandKnowledgeItemCommand(
                user_id=user_id,
                brand_id=brand_of(brand_id),
                shared_key=key_of(shared_key),
                request=body,
            )
        )

    @router.delete(ITEM_PATH, status_code=status.HTTP_204_NO_CONTENT)
    def delete_brand_knowledge_item(
        brand_id: str,
        shared_key: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        delete_item.operate(
            BrandKnowledgeItemCommand(
                user_id=user_id,
                brand_id=brand_of(brand_id),
                shared_key=key_of(shared_key),
            )
        )

    @router.post(
        f"{LOCATION_PATH}/knowledge/brand-overrides",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(OverrideBrandKnowledgeRequest),
    )
    def override_brand_knowledge(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[OverrideBrandKnowledgeRequest, Depends(read_override_body)],
    ) -> KnowledgeItemDetails:
        return override_item.operate(
            OverrideBrandKnowledgeCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(f"{LOCATION_PATH}/brand", status_code=status.HTTP_204_NO_CONTENT)
    def leave_brand_route(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        leave_brand.operate(
            LeaveBrandCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router

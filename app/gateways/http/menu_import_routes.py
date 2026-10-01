"""Menu import into the knowledge base (cabinet, concept section 3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsRequest,
    ConfirmImportedItemsResult,
    ImportMenuCommand,
    MenuImportRequest,
    MenuImportResult,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_menu_import_body = build_json_body_dependency(MenuImportRequest)
read_confirm_body = build_json_body_dependency(ConfirmImportedItemsRequest)


def build_menu_import_router(
    import_menu_operator: OperatorContract[ImportMenuCommand, MenuImportResult],
    confirm_imported_items_operator: OperatorContract[
        ConfirmImportedItemsCommand,
        ConfirmImportedItemsResult,
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token; owners and staff):
        POST /v1/businesses/{business_id}/knowledge/import
                {media_type, data_base64? | url?}   inactive drafts (201)
        POST /v1/businesses/{business_id}/knowledge/import/confirm
                {item_ids}                          activate checked drafts
    """

    router = APIRouter(tags=["knowledge"])

    @router.post(
        "/v1/businesses/{business_id}/knowledge/import",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(MenuImportRequest),
    )
    def import_menu(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[MenuImportRequest, Depends(read_menu_import_body)],
    ) -> MenuImportResult:
        return import_menu_operator.operate(
            ImportMenuCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/knowledge/import/confirm",
        openapi_extra=describe_json_body(ConfirmImportedItemsRequest),
    )
    def confirm_imported_items(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ConfirmImportedItemsRequest, Depends(read_confirm_body)],
    ) -> ConfirmImportedItemsResult:
        return confirm_imported_items_operator.operate(
            ConfirmImportedItemsCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                item_ids=list(body.item_ids),
            )
        )

    return router

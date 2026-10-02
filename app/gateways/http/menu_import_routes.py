"""Menu import into the knowledge base (cabinet, concept section 3)."""

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
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsRequest,
    ConfirmImportedItemsResult,
    DiscardedImportBatch,
    DiscardImportBatchCommand,
    ImportMenuCommand,
    MenuImportRequest,
    MenuImportResult,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.schemas.typings.users.prefixed_id import UserId

read_menu_import_body = build_json_body_dependency(MenuImportRequest)
read_confirm_body = build_json_body_dependency(ConfirmImportedItemsRequest)
IMPORT_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorBody,
        "description": (
            "The source cannot be read. For a link, reasons[].code is "
            "menu_link_invalid (not a public http(s) address), "
            "menu_link_unreachable (unknown host, timeout, no connection, HTTP "
            "error, redirect trouble) or menu_link_unreadable (too large, not "
            "a photo, PDF, text or web page), with details such as "
            "http_status:404 or media_type:application/zip."
        ),
    },
    status.HTTP_502_BAD_GATEWAY: {
        "model": ErrorBody,
        "description": "The menu model is unavailable (external_service_error).",
    },
}


def build_menu_import_router(
    import_menu_operator: OperatorContract[ImportMenuCommand, MenuImportResult],
    confirm_imported_items_operator: OperatorContract[
        ConfirmImportedItemsCommand,
        ConfirmImportedItemsResult,
    ],
    discard_import_batch_operator: OperatorContract[
        DiscardImportBatchCommand,
        DiscardedImportBatch,
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token; owners and staff):
        POST   /v1/businesses/{business_id}/knowledge/import
                  {media_type, data_base64? | url?}   inactive drafts and
                                                      their batch_id (201)
        POST   /v1/businesses/{business_id}/knowledge/import/confirm
                  {item_ids}                          activate checked drafts
        DELETE /v1/businesses/{business_id}/knowledge/import/{batch_id}
                                                      delete the drafts of an
                                                      import not confirmed
    A link that cannot be read is a 422 whose reasons name a
    MenuLinkProblem; an unavailable model is a 502.
    """

    router = APIRouter(tags=["knowledge"], responses=standard_error_responses())

    @router.post(
        "/v1/businesses/{business_id}/knowledge/import",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(MenuImportRequest),
        responses=IMPORT_RESPONSES,
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

    @router.delete(
        "/v1/businesses/{business_id}/knowledge/import/{batch_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def discard_import_batch(
        business_id: str,
        batch_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        discard_import_batch_operator.operate(
            DiscardImportBatchCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                batch_id=parse_path_identifier(
                    batch_id, MenuImportBatchId, "Menu import"
                ),
            )
        )

    return router

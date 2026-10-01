"""HTTP routes of the knowledge base (cabinet page /knowledge)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    DeleteKnowledgeItemCommand,
    KnowledgeItemDeletion,
    KnowledgeItemDetails,
    KnowledgeItemInput,
    KnowledgeItemList,
    KnowledgeItemListQuery,
    KnowledgeItemPatch,
    KnowledgeItemQuery,
    KnowledgeSearchInput,
    UpdateKnowledgeItemCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.knowledge.request_parsing import (
    json_body_openapi,
    parse_boolean_text,
    parse_json_body,
    parse_language_parameter,
    parse_path_value,
    parse_query_value,
)

type BusinessAccessOperator = OperatorContract[BusinessAccessRequest, BusinessDocument]


async def read_request_body(request: Request) -> bytes:
    """Raw request body; routes validate it in JSON mode against strict DTOs."""

    return await request.body()


def build_knowledge_router(
    current_user: CurrentUserDependency,
    business_access_operator: BusinessAccessOperator,
    list_knowledge_items_operator: OperatorContract[
        KnowledgeItemListQuery, KnowledgeItemList
    ],
    create_knowledge_item_operator: OperatorContract[
        CreateKnowledgeItemCommand, KnowledgeItemDetails
    ],
    get_knowledge_item_operator: OperatorContract[
        KnowledgeItemQuery, KnowledgeItemDetails
    ],
    update_knowledge_item_operator: OperatorContract[
        UpdateKnowledgeItemCommand, KnowledgeItemDetails
    ],
    delete_knowledge_item_operator: OperatorContract[
        DeleteKnowledgeItemCommand, KnowledgeItemDeletion
    ],
    search_knowledge_operator: OperatorContract[
        KnowledgeSearchRequest, KnowledgeSearchResult
    ],
) -> APIRouter:
    """
    Routes of the knowledge base: menu, services, rooms, packages, FAQ, rules.

    Owners and staff may read and edit it. Prices are integers in minor units
    of the business currency; `?language=` formats them (owner language by
    default). POST .../knowledge/search runs the same search as the
    assistant's search_knowledge tool, so the owner can test it.
    """

    router: APIRouter = APIRouter(tags=["knowledge"])

    def authorize(user_id: UserId, raw_business_id: str) -> BusinessDocument:
        business_id: BusinessId = parse_path_value(
            BusinessId,
            raw_business_id,
            "Business",
        )
        return business_access_operator.operate(
            BusinessAccessRequest(user_id=user_id, business_id=business_id)
        )

    @router.get("/v1/businesses/{business_id}/knowledge")
    def list_knowledge_items(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        kind: Annotated[str | None, Query()] = None,
        is_active: Annotated[str | None, Query()] = None,
        language: Annotated[str | None, Query()] = None,
    ) -> KnowledgeItemList:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_knowledge_items_operator.operate(
            KnowledgeItemListQuery(
                business_id=business.id,
                kind=parse_query_value(KnowledgeItemKind, kind, "kind"),
                is_active=parse_query_value(parse_boolean_text, is_active, "is_active"),
                language=parse_language_parameter(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/knowledge",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=json_body_openapi(KnowledgeItemInput),
    )
    def create_knowledge_item(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        raw_body: Annotated[bytes, Depends(read_request_body)],
        language: Annotated[str | None, Query()] = None,
    ) -> KnowledgeItemDetails:
        business: BusinessDocument = authorize(user_id, business_id)
        return create_knowledge_item_operator.operate(
            CreateKnowledgeItemCommand(
                business_id=business.id,
                item=parse_json_body(KnowledgeItemInput, raw_body),
                language=parse_language_parameter(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/knowledge/search",
        openapi_extra=json_body_openapi(KnowledgeSearchInput),
    )
    def search_knowledge(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        raw_body: Annotated[bytes, Depends(read_request_body)],
    ) -> KnowledgeSearchResult:
        business: BusinessDocument = authorize(user_id, business_id)
        search_input: KnowledgeSearchInput = parse_json_body(
            KnowledgeSearchInput,
            raw_body,
        )
        return search_knowledge_operator.operate(
            KnowledgeSearchRequest(
                business_id=business.id,
                query=search_input.query,
                language=search_input.language or business.owner_language,
                limit=search_input.limit,
            )
        )

    @router.get("/v1/businesses/{business_id}/knowledge/{item_id}")
    def get_knowledge_item(
        business_id: str,
        item_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> KnowledgeItemDetails:
        business: BusinessDocument = authorize(user_id, business_id)
        return get_knowledge_item_operator.operate(
            KnowledgeItemQuery(
                business_id=business.id,
                item_id=parse_path_value(KnowledgeItemId, item_id, "Knowledge item"),
                language=parse_language_parameter(language),
            )
        )

    @router.patch(
        "/v1/businesses/{business_id}/knowledge/{item_id}",
        openapi_extra=json_body_openapi(KnowledgeItemPatch),
    )
    def update_knowledge_item(
        business_id: str,
        item_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        raw_body: Annotated[bytes, Depends(read_request_body)],
        language: Annotated[str | None, Query()] = None,
    ) -> KnowledgeItemDetails:
        business: BusinessDocument = authorize(user_id, business_id)
        return update_knowledge_item_operator.operate(
            UpdateKnowledgeItemCommand(
                business_id=business.id,
                item_id=parse_path_value(KnowledgeItemId, item_id, "Knowledge item"),
                patch=parse_json_body(KnowledgeItemPatch, raw_body),
                language=parse_language_parameter(language),
            )
        )

    @router.delete(
        "/v1/businesses/{business_id}/knowledge/{item_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_knowledge_item(
        business_id: str,
        item_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        business: BusinessDocument = authorize(user_id, business_id)
        delete_knowledge_item_operator.operate(
            DeleteKnowledgeItemCommand(
                business_id=business.id,
                item_id=parse_path_value(KnowledgeItemId, item_id, "Knowledge item"),
            )
        )

    return router

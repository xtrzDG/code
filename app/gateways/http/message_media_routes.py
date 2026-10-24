"""The files customers sent (voice notes, photos), opened from the cabinet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.media import MessageMediaQuery, StoredMediaFile
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.users.prefixed_id import UserId

# Personal data: no HTTP cache keeps it; a file is shown inline and never
# sniffed as another type (only audio and pictures are ever stored).
MEDIA_RESPONSE_HEADERS: dict[str, str] = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Disposition": "inline",
    "Content-Security-Policy": "default-src 'none'; sandbox",
}
MEDIA_OPENAPI_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The voice note or photo as the customer sent it.",
        "content": {
            "audio/*": {"schema": {"type": "string", "format": "binary"}},
            "image/*": {"schema": {"type": "string", "format": "binary"}},
        },
    },
}


def build_message_media_router(
    get_message_media_operator: OperatorContract[MessageMediaQuery, StoredMediaFile],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token; owners and staff):
        GET  /v1/businesses/{business_id}/media/{media_id}
                                    a voice note or photo of a customer
                                    message (audited); 404 once the
                                    retention purge or an erasure removed it
    """

    router = APIRouter(tags=["conversations"], responses=standard_error_responses())

    @router.get(
        "/v1/businesses/{business_id}/media/{media_id}",
        response_class=Response,
        responses=MEDIA_OPENAPI_RESPONSES,
    )
    def get_message_media(
        request: Request,
        business_id: str,
        media_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        media: StoredMediaFile = get_message_media_operator.operate(
            MessageMediaQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                media_id=parse_path_identifier(media_id, MessageMediaId, "File"),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(
            content=media.content,
            media_type=str(media.media_type),
            headers=MEDIA_RESPONSE_HEADERS,
        )

    return router

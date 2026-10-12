"""Photos and voice notes website chat visitors upload (public, no bearer token)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request, Response, status
from starlette.concurrency import run_in_threadpool

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.channel_routes import parse_session_key
from app.gateways.http.multipart_upload import (
    FILE_FIELD_NAME,
    UploadedFilePart,
    parse_file_part,
    read_limited_body,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.widget_cors_middleware import (
    WIDGET_CORS_HEADERS,
    WIDGET_SESSION_KEY_HEADER,
)
from app.gateways.http.widget_origin_guard import WidgetOriginGuard
from app.schemas.dto.channels.widget_uploads import (
    WidgetAttachmentView,
    WidgetUploadAdmission,
    WidgetUploadAllowance,
    WidgetUploadCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.media.strings import DeclaredUploadType

WIDGET_ATTACHMENTS_PATH: str = "/v1/widget/{business_id}/attachments"
UPLOAD_REQUEST_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": [FILE_FIELD_NAME],
                    "properties": {
                        FILE_FIELD_NAME: {"type": "string", "format": "binary"}
                    },
                }
            }
        },
    }
}


def build_widget_attachment_router(
    admit_widget_upload_operator: OperatorContract[
        WidgetUploadAdmission, WidgetUploadAllowance
    ],
    accept_widget_upload_operator: OperatorContract[
        WidgetUploadCommand, WidgetAttachmentView
    ],
    widget_origin_guard: WidgetOriginGuard | None = None,
) -> APIRouter:
    """
    Routes (public; the visitor is the X-Widget-Session-Key header):
        POST /v1/widget/{business_id}/attachments
            One photo (JPEG, PNG, WebP) or voice note (WebM, Ogg, MP4) as
            the multipart part `file`, for the visitor's next message to
            name (201, `attachment_id`). Counted and checked (429, 404,
            409) before the file is read; the file is then refused when
            its bytes are not the type it was declared as, it is over the
            cap of its kind or a voice note is too long (422 with the
            reason's code). Refused to a website the business does not
            allow (403).
    """

    router: APIRouter = APIRouter(
        tags=["channels"], responses=standard_error_responses()
    )
    guarded = [] if widget_origin_guard is None else [Depends(widget_origin_guard)]

    @router.options(WIDGET_ATTACHMENTS_PATH, include_in_schema=False)
    def allow_widget_upload_preflight(business_id: str) -> Response:
        del business_id
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers=WIDGET_CORS_HEADERS,
        )

    @router.post(
        WIDGET_ATTACHMENTS_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=UPLOAD_REQUEST_BODY,
        dependencies=guarded,
    )
    async def upload_widget_attachment(
        request: Request,
        business_id: str,
        response: Response,
        session_key: Annotated[str, Header(alias=WIDGET_SESSION_KEY_HEADER)],
    ) -> WidgetAttachmentView:
        response.headers.update(WIDGET_CORS_HEADERS)
        business: BusinessId = parse_path_identifier(business_id, BusinessId, "Chat")
        visitor: WidgetSessionKey = parse_session_key(session_key)
        allowance: WidgetUploadAllowance = await run_in_threadpool(
            admit_widget_upload_operator.operate,
            WidgetUploadAdmission(
                business_id=business,
                session_key=visitor,
                client_ip_address=read_client_ip_address(request),
            ),
        )
        body: bytes = await read_limited_body(request, int(allowance.max_file_bytes))
        part: UploadedFilePart = parse_file_part(
            body, request.headers.get("content-type")
        )
        return await run_in_threadpool(
            accept_widget_upload_operator.operate,
            WidgetUploadCommand(
                business_id=business,
                session_key=visitor,
                content=part.content,
                declared_type=(
                    None
                    if part.declared_type is None
                    else DeclaredUploadType(part.declared_type)
                ),
            ),
        )

    return router

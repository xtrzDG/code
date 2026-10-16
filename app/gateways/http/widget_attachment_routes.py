"""Photos and voice notes website chat visitors upload (public, no bearer token)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request, Response, status
from starlette.concurrency import run_in_threadpool

from app.contracts.operator_contract import OperatorContract
from app.contracts.widget_upload_slots import WidgetUploadSlotsFacilitatorContract
from app.gateways.http.channel_routes import parse_session_key
from app.gateways.http.multipart_file_stream import MultipartFileStream
from app.gateways.http.multipart_upload import FILE_FIELD_NAME
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
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.media.strings import DeclaredUploadType

WIDGET_ATTACHMENTS_PATH: str = "/v1/widget/{business_id}/attachments"
# A photo or a voice note of the largest size over a slow phone connection;
# a body that trickles in slower would hold one of the few upload places.
UPLOAD_READ_SECONDS: float = 120.0
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
    upload_slots: WidgetUploadSlotsFacilitatorContract,
    widget_origin_guard: WidgetOriginGuard | None = None,
    upload_read_seconds: float = UPLOAD_READ_SECONDS,
) -> APIRouter:
    """
    Routes (public; the visitor is the X-Widget-Session-Key header):
        POST /v1/widget/{business_id}/attachments
            One photo (JPEG, PNG, WebP) or voice note (Opus in WebM or Ogg,
            AAC or Opus in MP4) as the multipart part `file`, for the
            visitor's next message to name (201, `attachment_id`). Each
            upload takes one of the process's few places first
            (MEDIA_MAX_CONCURRENT_UPLOADS, at most two per client network;
            429 at once when they are taken). The part's headers are read,
            then the upload is counted and checked (429, 404, 409, and 422
            `unsupported_type` for a type the chat does not take) before
            the file is read, and the file is read only up to the cap of
            the kind its part declares (422 `file_too_large` as soon as it
            passes it; `upload_too_slow` for a body that has not arrived
            within `upload_read_seconds`). The file is then refused when
            its bytes are not the type it was declared as or a voice note
            is too long, measured from its audio (422 with the reason's
            code). Refused to a website the business does not allow (403).
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
        client: ClientIpAddress | None = read_client_ip_address(request)
        with upload_slots.hold(client):
            form = MultipartFileStream(
                request.stream(),
                request.headers.get("content-type"),
                request.headers.get("content-length"),
                upload_read_seconds,
            )
            declared: str | None = await form.read_head()
            declared_type: DeclaredUploadType | None = (
                None if declared is None else DeclaredUploadType(declared)
            )
            allowance: WidgetUploadAllowance = await run_in_threadpool(
                admit_widget_upload_operator.operate,
                WidgetUploadAdmission(
                    business_id=business,
                    session_key=visitor,
                    client_ip_address=client,
                    declared_type=declared_type,
                ),
            )
            content: bytes = await form.read_file(allowance.max_file_bytes)
            return await run_in_threadpool(
                accept_widget_upload_operator.operate,
                WidgetUploadCommand(
                    business_id=business,
                    session_key=visitor,
                    content=content,
                    declared_type=declared_type,
                ),
            )

    return router

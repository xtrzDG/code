"""
The full export of a business (Settings → Privacy):

    POST /v1/businesses/{business_id}/business-exports   {language?}
        202: the export, queued (or the one already queued or running);
        owners only, after a recent sign-in or step-up (401 step_up_required)
    GET  /v1/businesses/{business_id}/business-exports
        the latest exports, a READY one with its signed download path
    GET  /v1/business-exports/{business_id}/{export_id}/download?token=...
        the ZIP, without a session: the token is the permission; 404 when
        it is not this export's, expired, or the archive was purged
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.privacy.business_exports import (
    BusinessExportDownload,
    BusinessExportDownloadQuery,
    BusinessExportList,
    BusinessExportListQuery,
    BusinessExportView,
    StartBusinessExportCommand,
    StartBusinessExportRequest,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.constrained_strings import BusinessExportToken
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.users.prefixed_id import UserId

B: str = "/v1/businesses/{business_id}"
ZIP_RESPONSE: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The export's ZIP archive.",
        "content": {"application/zip": {"schema": {"type": "string"}}},
    }
}
# A download is personal data: never cached, indexed or told where it came from.
DOWNLOAD_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex",
    "Referrer-Policy": "no-referrer",
}

read_start_body = build_json_body_dependency(StartBusinessExportRequest, optional=True)


def build_business_export_router(
    *,
    current_user: CurrentUserDependency,
    start_export: OperatorContract[StartBusinessExportCommand, BusinessExportView],
    list_exports: OperatorContract[BusinessExportListQuery, BusinessExportList],
    download_export: OperatorContract[
        BusinessExportDownloadQuery, BusinessExportDownload
    ],
) -> APIRouter:
    router = APIRouter(tags=["exports"], responses=standard_error_responses())

    @router.post(
        f"{B}/business-exports",
        status_code=status.HTTP_202_ACCEPTED,
        openapi_extra=describe_json_body(StartBusinessExportRequest, optional=True),
    )
    def start_business_export(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[StartBusinessExportRequest, Depends(read_start_body)],
    ) -> BusinessExportView:
        return start_export.operate(
            StartBusinessExportCommand(
                user_id=user_id,
                business_id=parse_business(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(f"{B}/business-exports")
    def list_business_exports(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessExportList:
        return list_exports.operate(
            BusinessExportListQuery(
                user_id=user_id, business_id=parse_business(business_id)
            )
        )

    @router.get(
        "/v1/business-exports/{business_id}/{export_id}/download",
        response_class=Response,
        responses=ZIP_RESPONSE,
    )
    def download_business_export(
        request: Request,
        business_id: str,
        export_id: str,
        token: str = "",
    ) -> Response:
        download: BusinessExportDownload = download_export.operate(
            BusinessExportDownloadQuery(
                business_id=parse_business(business_id),
                export_id=parse_path_identifier(export_id, BusinessExportId, "Export"),
                token=parse_token(token),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(
            content=download.content,
            media_type="application/zip",
            headers={
                **DOWNLOAD_HEADERS,
                "Content-Disposition": (f'attachment; filename="{download.file_name}"'),
            },
        )

    return router


def parse_business(raw_business_id: str) -> BusinessId:
    return parse_path_identifier(raw_business_id, BusinessId, "Business")


def parse_token(raw_token: str) -> BusinessExportToken:
    """A malformed token is the same 404 as a wrong or expired one."""

    try:
        return BusinessExportToken(raw_token)
    except ValueError as error:
        raise NotFoundError(
            "This download link is not valid or has expired."
        ) from error

"""Deleting one's own account, and the certificates of deleted businesses."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.csv_streaming import attachment_disposition
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.business_closures.account_deletion import (
    DeleteCurrentUserCommand,
)
from app.schemas.dto.business_closures.business_deletions import (
    BusinessDeletionList,
    DeletionCertificateFile,
    DeletionCertificateQuery,
)
from app.schemas.typings.business_closures.prefixed_id import BusinessDeletionId
from app.schemas.typings.users.prefixed_id import UserId

PDF_MEDIA_TYPE: str = "application/pdf"
CERTIFICATE_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The deletion certificate as a PDF file.",
        "content": {PDF_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
    },
}


def build_account_deletion_router(
    delete_current_user_operator: OperatorContract[DeleteCurrentUserCommand, None],
    list_business_deletions_operator: OperatorContract[UserId, BusinessDeletionList],
    get_deletion_certificate_operator: OperatorContract[
        DeletionCertificateQuery, DeletionCertificateFile
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        DELETE /v1/me  delete the signed-in person's account: sessions,
               authenticator, recovery codes, passkeys, notification devices
               and preferences, then the account (step-up; 409 while they are
               the last owner of a business that is not closing; 204)
        GET    /v1/me/business-deletions  the businesses they owned that were
               deleted (or are being deleted), newest first
        GET    /v1/me/business-deletions/{deletion_id}/certificate  the
               deletion certificate as a PDF (?language=, else theirs)
    """

    router = APIRouter(tags=["auth"], responses=standard_error_responses())

    @router.delete("/v1/me", status_code=status.HTTP_204_NO_CONTENT)
    def delete_current_user(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        delete_current_user_operator.operate(
            DeleteCurrentUserCommand(
                user_id=user_id, client_ip_address=read_client_ip_address(request)
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/v1/me/business-deletions")
    def list_business_deletions(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessDeletionList:
        return list_business_deletions_operator.operate(user_id)

    @router.get(
        "/v1/me/business-deletions/{deletion_id}/certificate",
        response_class=Response,
        responses=CERTIFICATE_RESPONSES,
    )
    def get_deletion_certificate(
        deletion_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> Response:
        query = DeletionCertificateQuery(
            user_id=user_id,
            deletion_id=parse_path_identifier(
                deletion_id, BusinessDeletionId, "Deletion"
            ),
            language=parse_language_parameter(language),
        )
        certificate: DeletionCertificateFile = (
            get_deletion_certificate_operator.operate(query)
        )
        return Response(
            content=certificate.content,
            media_type=PDF_MEDIA_TYPE,
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": attachment_disposition(
                    str(certificate.file_name)
                ),
            },
        )

    return router

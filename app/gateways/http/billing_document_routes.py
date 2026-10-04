"""Billing details on invoices and the invoice and receipt PDFs (owners)."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.dto.billing_profiles import (
    BillingProfileQuery,
    BillingProfileRequest,
    BillingProfileView,
    SaveBillingProfileCommand,
)
from app.schemas.dto.invoicing import BillingDocumentFile, BillingDocumentQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.localization.language_tags import parse_language_tag

PDF_MEDIA_TYPE: str = "application/pdf"
PDF_OPENAPI_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The invoice or receipt as a PDF file.",
        "content": {PDF_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
    },
}

type BillingProfileOperator = OperatorContract[BillingProfileQuery, BillingProfileView]
type SaveBillingProfileOperator = OperatorContract[
    SaveBillingProfileCommand, BillingProfileView
]
type BillingDocumentOperator = OperatorContract[
    BillingDocumentQuery, BillingDocumentFile
]
read_billing_profile_body = build_json_body_dependency(BillingProfileRequest)


def build_billing_document_router(
    get_billing_profile_operator: BillingProfileOperator,
    save_billing_profile_operator: SaveBillingProfileOperator,
    get_billing_document_operator: BillingDocumentOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a business owner):
        GET /v1/businesses/{business_id}/billing/profile
            the details invoices print about the business, and their VAT
        PUT /v1/businesses/{business_id}/billing/profile
            save them (audited); invoices already issued keep theirs
        GET /v1/businesses/{business_id}/billing/invoices/{invoice_id}
            /documents/{document_kind}?language=
            the PDF of the invoice (`invoice`) or, once paid, of its receipt
            (`receipt`; 409 before); audited as an export

    `language` is a BCP 47 tag (default: the owner language); the PDFs are
    written in English, Russian and Georgian, other languages read English.
    """

    router = APIRouter(tags=["billing"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/billing/profile")
    def get_billing_profile(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BillingProfileView:
        return get_billing_profile_operator.operate(
            BillingProfileQuery(
                user_id=user_id, business_id=parse_business_id(business_id)
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/billing/profile",
        openapi_extra=describe_json_body(BillingProfileRequest),
    )
    def save_billing_profile(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[BillingProfileRequest, Depends(read_billing_profile_body)],
    ) -> BillingProfileView:
        return save_billing_profile_operator.operate(
            SaveBillingProfileCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(
        "/v1/businesses/{business_id}/billing/invoices/{invoice_id}"
        "/documents/{document_kind}",
        response_class=Response,
        responses=PDF_OPENAPI_RESPONSES,
    )
    def get_billing_document(
        business_id: str,
        invoice_id: str,
        document_kind: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> Response:
        document: BillingDocumentFile = get_billing_document_operator.operate(
            BillingDocumentQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                invoice_id=parse_path_identifier(invoice_id, InvoiceId, "Invoice"),
                kind=parse_document_kind(document_kind),
                display_language=parse_optional_language(language),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(
            content=document.content,
            media_type=PDF_MEDIA_TYPE,
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": attachment_disposition(str(document.file_name)),
            },
        )

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    return parse_path_identifier(raw_business_id, BusinessId, "Business")


def parse_document_kind(raw_kind: str) -> BillingDocumentKind:
    """`invoice` or `receipt`; anything else is an unknown document (404)."""

    try:
        return BillingDocumentKind(raw_kind)
    except ValueError as error:
        raise NotFoundError("Unknown billing document.") from error


def parse_optional_language(raw_language: str | None) -> LanguageTag | None:
    if raw_language is None or raw_language.strip() == "":
        return None

    return parse_language_tag(raw_language)


def attachment_disposition(file_name: str) -> str:
    """A download under the given (ASCII) name."""

    return f"attachment; filename=\"{file_name}\"; filename*=UTF-8''{quote(file_name)}"

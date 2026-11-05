"""Customers → Segments: saved groups of customers, their members and CSV."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.csv_streaming import attachment_disposition, stream_csv
from app.gateways.http.export_routes import CSV_MEDIA_TYPE, CSV_RESPONSE
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.query_values import OptionalQuery
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.contacts import ContactPage
from app.schemas.dto.customers.customer_segments import (
    CreateSegmentCommand,
    SegmentExportPageQuery,
    SegmentList,
    SegmentListQuery,
    SegmentMembersQuery,
    SegmentPreview,
    SegmentPreviewCommand,
    SegmentQuery,
    SegmentRequest,
    SegmentRulesBody,
    SegmentView,
    StartSegmentExportCommand,
    UpdateSegmentCommand,
)
from app.schemas.dto.privacy.csv_exports import CsvExportHeader, CsvExportPage
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import CustomerSegmentId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.localization.language_tags import parse_language_tag

S: str = "/v1/businesses/{business_id}/customer-segments"
DEFAULT_LANGUAGE: LanguageTag = LanguageTag("en")

read_segment_body = build_json_body_dependency(SegmentRequest)
read_rules_body = build_json_body_dependency(SegmentRulesBody)


def build_customer_segment_router(
    *,
    current_user: CurrentUserDependency,
    list_segments: OperatorContract[SegmentListQuery, SegmentList],
    create_segment: OperatorContract[CreateSegmentCommand, SegmentView],
    update_segment: OperatorContract[UpdateSegmentCommand, SegmentView],
    delete_segment: OperatorContract[SegmentQuery, None],
    list_members: OperatorContract[SegmentMembersQuery, ContactPage],
    preview_segment: OperatorContract[SegmentPreviewCommand, SegmentPreview],
    start_export: OperatorContract[StartSegmentExportCommand, CsvExportHeader],
    read_export_page: OperatorContract[SegmentExportPageQuery, CsvExportPage],
) -> APIRouter:
    """
    Routes (Bearer auth; owners):
        GET    {S}                          saved segments and the business's tags
        POST   {S}                          save one (201)
        POST   {S}/preview                  how many customers rules hold
        PUT    {S}/{segment_id}             rename or change its rules
        DELETE {S}/{segment_id}             delete it (204)
        GET    {S}/{segment_id}/members?limit=&cursor=   its customers, a page
        GET    {S}/{segment_id}/export?language=  its customers as CSV (step-up)
    """

    router = APIRouter(tags=["customers"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    def segment(raw_id: str) -> CustomerSegmentId:
        return parse_path_identifier(raw_id, CustomerSegmentId, "Segment")

    @router.get(S)
    def list_customer_segments(
        business_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> SegmentList:
        return list_segments.operate(
            SegmentListQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.post(
        S,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(SegmentRequest),
    )
    def create_customer_segment(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[SegmentRequest, Depends(read_segment_body)],
    ) -> SegmentView:
        return create_segment.operate(
            CreateSegmentCommand(
                user_id=user_id,
                business_id=business(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(f"{S}/preview", openapi_extra=describe_json_body(SegmentRulesBody))
    def preview_customer_segment(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[SegmentRulesBody, Depends(read_rules_body)],
    ) -> SegmentPreview:
        return preview_segment.operate(
            SegmentPreviewCommand(
                user_id=user_id,
                business_id=business(business_id),
                rules=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.put(f"{S}/{{segment_id}}", openapi_extra=describe_json_body(SegmentRequest))
    def update_customer_segment(
        business_id: str,
        segment_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[SegmentRequest, Depends(read_segment_body)],
    ) -> SegmentView:
        return update_segment.operate(
            UpdateSegmentCommand(
                user_id=user_id,
                business_id=business(business_id),
                segment_id=segment(segment_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(f"{S}/{{segment_id}}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_customer_segment(
        business_id: str,
        segment_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        delete_segment.operate(
            SegmentQuery(
                user_id=user_id,
                business_id=business(business_id),
                segment_id=segment(segment_id),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(f"{S}/{{segment_id}}/members")
    def list_customer_segment_members(
        business_id: str,
        segment_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> ContactPage:
        return list_members.operate(
            SegmentMembersQuery(
                user_id=user_id,
                business_id=business(business_id),
                segment_id=segment(segment_id),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(
        f"{S}/{{segment_id}}/export",
        response_class=StreamingResponse,
        responses=CSV_RESPONSE,
    )
    def export_customer_segment(
        business_id: str,
        segment_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        language: OptionalQuery = None,
    ) -> StreamingResponse:
        owner_business: BusinessId = business(business_id)
        segment_key: CustomerSegmentId = segment(segment_id)
        header: CsvExportHeader = start_export.operate(
            StartSegmentExportCommand(
                user_id=user_id,
                business_id=owner_business,
                segment_id=segment_key,
                language=(
                    DEFAULT_LANGUAGE
                    if language is None or language.strip() == ""
                    else parse_language_tag(language)
                ),
                client_ip_address=read_client_ip_address(request),
            )
        )

        def read_page(page_cursor: PageCursor | None) -> CsvExportPage:
            return read_export_page.operate(
                SegmentExportPageQuery(
                    user_id=user_id,
                    business_id=owner_business,
                    segment_id=segment_key,
                    cursor=page_cursor,
                )
            )

        return StreamingResponse(
            stream_csv(header, read_page),
            media_type=CSV_MEDIA_TYPE,
            headers={
                "Content-Disposition": attachment_disposition(str(header.file_name)),
                "Cache-Control": "no-store",
            },
        )

    return router

"""
The cabinet's tables as CSV downloads (Bookings, Leads, Customers, the
inbox's conversations with their messages, the audit log), with the same
query filters as the lists:

    GET /v1/businesses/{business_id}/exports/{table}
        table: bookings | leads | contacts | conversations | audit_log
        language: headings' language (en by default)
        bookings: from, to, status, resource_id, include_sandbox, order
        leads: status, include_sandbox
        contacts: search
        conversations: view, channel
        audit_log: action, entity, actor_id, since, until

Owners only, after a recent sign-in or step-up (401 step_up_required);
audited once as an export. The body is streamed a page at a time
(text/csv, UTF-8 with a byte order mark, formulas defused).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.compliance_routes import parse_optional_moment
from app.gateways.http.conversations.feed_query_values import parse_channel
from app.gateways.http.csv_streaming import attachment_disposition, stream_csv
from app.gateways.http.inbox_routes import parse_view
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.query_values import (
    OptionalQuery,
    parse_flag,
    parse_optional_text,
)
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.bookings import BookingOrder, BookingStatus, LeadStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.dto.privacy.csv_exports import (
    CsvExportFilters,
    CsvExportHeader,
    CsvExportPage,
    CsvExportPageQuery,
    StartCsvExportCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.localization.language_tags import parse_language_tag

CSV_MEDIA_TYPE: str = "text/csv; charset=utf-8"
DEFAULT_LANGUAGE: LanguageTag = LanguageTag("en")
CSV_RESPONSE: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The table as CSV (UTF-8 with a byte order mark).",
        "content": {"text/csv": {"schema": {"type": "string"}}},
    }
}


def build_export_router(
    *,
    current_user: CurrentUserDependency,
    start_csv_export: OperatorContract[StartCsvExportCommand, CsvExportHeader],
    read_csv_export_page: OperatorContract[CsvExportPageQuery, CsvExportPage],
) -> APIRouter:
    router = APIRouter(tags=["exports"], responses=standard_error_responses())

    @router.get(
        "/v1/businesses/{business_id}/exports/{table}",
        response_class=StreamingResponse,
        responses=CSV_RESPONSE,
    )
    def export_table(
        request: Request,
        business_id: str,
        table: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: OptionalQuery = None,
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
        status: OptionalQuery = None,
        resource_id: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        order: OptionalQuery = None,
        search: OptionalQuery = None,
        view: OptionalQuery = None,
        channel: OptionalQuery = None,
        action: OptionalQuery = None,
        entity: OptionalQuery = None,
        actor_id: OptionalQuery = None,
        since: OptionalQuery = None,
        until: OptionalQuery = None,
    ) -> StreamingResponse:
        kind: CsvExportKind = parse_kind(table)
        business: BusinessId = parse_path_identifier(
            business_id, BusinessId, "Business"
        )
        is_bookings: bool = kind is CsvExportKind.BOOKINGS
        filters = CsvExportFilters(
            date_from=parse_optional_text(date_from, LocalDate, "from"),
            date_to=parse_optional_text(date_to, LocalDate, "to"),
            booking_status=(
                parse_optional_text(status, BookingStatus, "status")
                if is_bookings
                else None
            ),
            lead_status=(
                parse_optional_text(status, LeadStatus, "status")
                if kind is CsvExportKind.LEADS
                else None
            ),
            resource_id=parse_optional_text(resource_id, ResourceId, "resource_id"),
            include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
            order=parse_optional_text(order, BookingOrder, "order")
            or BookingOrder.EARLIEST_FIRST,
            search=parse_optional(
                None if search is None else search.strip(), ContactSearchText, "search"
            ),
            view=parse_view(view),
            channel=parse_channel(channel),
            action=parse_optional(action, AuditAction, "action"),
            entity=parse_optional(entity, AuditEntityName, "entity"),
            actor_id=parse_optional(actor_id, UserId, "actor_id"),
            since=parse_optional_moment(since, "since"),
            until=parse_optional_moment(until, "until"),
        )
        header: CsvExportHeader = start_csv_export.operate(
            StartCsvExportCommand(
                user_id=user_id,
                business_id=business,
                kind=kind,
                language=(
                    DEFAULT_LANGUAGE
                    if language is None or language.strip() == ""
                    else parse_language_tag(language)
                ),
                filters=filters,
                client_ip_address=read_client_ip_address(request),
            )
        )

        def read_page(cursor: PageCursor | None) -> CsvExportPage:
            return read_csv_export_page.operate(
                CsvExportPageQuery(
                    user_id=user_id,
                    business_id=business,
                    kind=kind,
                    filters=filters,
                    cursor=cursor,
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


def parse_kind(raw_kind: str) -> CsvExportKind:
    """An unknown table is a missing resource (404)."""

    try:
        return CsvExportKind(raw_kind)
    except ValueError as error:
        raise NotFoundError(f"Export {raw_kind} was not found.") from error

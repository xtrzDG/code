"""
CSV exports of the cabinet's lists: the owner starts one (authorized,
stepped up and audited once), then the table is read a keyset page at a
time and streamed, so no export holds the whole table in memory.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingOrder, BookingStatus, LeadStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import InboxView
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName, ClientIpAddress
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.privacy.constrained_strings import ExportFileName
from app.schemas.typings.privacy.strings import CsvCellText, CsvColumnTitle
from app.schemas.typings.users.prefixed_id import UserId


class CsvExportFilters(ImmutableDTO):
    """
    The filters of the list the table copies, as its query names them:
    bookings by local start dates, status, resource and order; leads by
    status; both with sandbox ones on request; contacts by a search;
    conversations by inbox view and channel; the audit log by operation,
    entity type, person and period. A filter of another list is ignored.
    """

    date_from: LocalDate | None = None
    date_to: LocalDate | None = None
    booking_status: BookingStatus | None = None
    resource_id: ResourceId | None = None
    order: BookingOrder = BookingOrder.EARLIEST_FIRST
    lead_status: LeadStatus | None = None
    include_sandbox: IsSandboxIncluded = False
    search: ContactSearchText | None = None
    view: InboxView = InboxView.ALL
    channel: ChannelKind | None = None
    action: AuditAction | None = None
    entity: AuditEntityName | None = None
    actor_id: UserId | None = None
    since: Microseconds | None = None
    until: Microseconds | None = None


class StartCsvExportCommand(ImmutableDTO):
    """
    The owner downloads one table: allowed to owners only, after a recent
    sign-in or step-up, and written to the audit log as an export.
    `language` is the language of the column headings.
    """

    user_id: UserId
    business_id: BusinessId
    kind: CsvExportKind
    language: LanguageTag
    filters: CsvExportFilters = Field(default_factory=CsvExportFilters)
    client_ip_address: ClientIpAddress | None = None


class CsvExportHeader(ImmutableDTO):
    """The file name a download is saved under and the table's headings."""

    file_name: ExportFileName
    columns: list[CsvColumnTitle] = Field(default_factory=list[CsvColumnTitle])


class CsvExportPageQuery(ImmutableDTO):
    """
    One keyset page of the rows of a started export, after `cursor` (the
    previous page's `next_cursor`; None for the first). The page size is
    the table's own.
    """

    user_id: UserId
    business_id: BusinessId
    kind: CsvExportKind
    filters: CsvExportFilters = Field(default_factory=CsvExportFilters)
    cursor: PageCursor | None = None


class CsvRow(ImmutableDTO):
    """One row of a table, its cells in the order of the headings."""

    cells: list[CsvCellText] = Field(default_factory=list[CsvCellText])


class CsvExportPage(ImmutableDTO):
    """
    Rows of one page; `next_cursor` is None after the last. A page can
    hold fewer rows than asked (records of erased customers are left out).
    """

    rows: list[CsvRow] = Field(default_factory=list[CsvRow])
    next_cursor: PageCursor | None = None

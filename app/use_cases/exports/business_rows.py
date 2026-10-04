"""
Rows of the bookings and leads tables: the same keyset pages as the
cabinet's lists (same filters, same order), each record with its customer
and place; records of erased customers are left out.
"""

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.privacy.csv_exports import (
    CsvExportFilters,
    CsvExportPage,
    CsvExportPageQuery,
    CsvRow,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.use_cases.shared.booking_listing import page_bookings
from app.utilities.paging.keyset_paging import finish_page, read_slice
from app.utilities.privacy.csv_cells import (
    amount_cell,
    flag_cell,
    moment_cell,
    text_cell,
)
from app.utilities.scheduling.booking_views import build_booking_view


def is_erased(contact: ContactDocument | None) -> bool:
    """The record's customer asked to be forgotten: their rows stay out."""

    return contact is not None and contact.erased_at is not None


@dataclass(frozen=True)
class BookingRows:
    booking_repo: BookingRepoContract
    resource_repo: ResourceRepoContract
    knowledge_item_repo: KnowledgeItemRepoContract
    contact_repo: ContactRepoContract

    def read(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        query: CsvExportPageQuery,
        page: PageRequest,
    ) -> CsvExportPage:
        filters: CsvExportFilters = query.filters
        bookings, next_cursor = page_bookings(
            self.booking_repo,
            business.id,
            zone,
            page,
            date_from_text=filters.date_from,
            date_to_text=filters.date_to,
            status=filters.booking_status,
            resource_id=filters.resource_id,
            include_sandbox=filters.include_sandbox,
            order=filters.order,
        )
        contacts: dict[ContactId, ContactDocument] = self.contact_repo.get_many(
            business.id, [booking.contact_id for booking in bookings]
        )
        services: dict[KnowledgeItemId, KnowledgeItemDocument] = (
            self.knowledge_item_repo.get_many(
                business.id,
                [
                    booking.service_item_id
                    for booking in bookings
                    if booking.service_item_id is not None
                ],
            )
        )
        resources = {
            resource.id: resource
            for resource in self.resource_repo.list_by_business(business.id)
        }
        rows: list[CsvRow] = []
        for booking in bookings:
            contact: ContactDocument | None = contacts.get(booking.contact_id)
            if is_erased(contact):
                continue

            view: BookingView = build_booking_view(
                booking,
                business.timezone,
                zone,
                resources.get(booking.resource_id),
                contact,
                _service_of(booking, services),
            )
            rows.append(booking_row(view, zone))

        return CsvExportPage(rows=rows, next_cursor=next_cursor)


def _service_of(
    booking: BookingDocument, services: dict[KnowledgeItemId, KnowledgeItemDocument]
) -> KnowledgeItemDocument | None:
    if booking.service_item_id is None:
        return None

    return services.get(booking.service_item_id)


def booking_row(view: BookingView, zone: ZoneInfo) -> CsvRow:
    return CsvRow(
        cells=[
            text_cell(view.id),
            text_cell(view.date),
            text_cell(view.time),
            text_cell(view.end_date),
            text_cell(view.end_time),
            text_cell(view.status),
            text_cell(view.resource_name),
            text_cell(view.service_title),
            text_cell(view.party_size),
            text_cell(view.contact_name),
            text_cell(view.contact_phone_number),
            text_cell(view.source_channel),
            amount_cell(view.value_minor, view.currency_code),
            text_cell(view.currency_code),
            text_cell(view.notes),
            flag_cell(view.is_sandbox),
            moment_cell(view.created_at, zone),
        ]
    )


@dataclass(frozen=True)
class LeadRows:
    lead_repo: LeadRepoContract
    contact_repo: ContactRepoContract

    def read(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        query: CsvExportPageQuery,
        page: PageRequest,
    ) -> CsvExportPage:
        filters: CsvExportFilters = query.filters
        leads: list[LeadDocument]
        leads, next_cursor = finish_page(
            self.lead_repo.page_by_business(
                business.id,
                read_slice(page),
                filters.lead_status,
                filters.include_sandbox,
            ),
            page,
            sort_key=lambda lead: int(lead.created_at),
            item_id=lambda lead: str(lead.id),
        )
        contacts: dict[ContactId, ContactDocument] = self.contact_repo.get_many(
            business.id, [lead.contact_id for lead in leads]
        )
        rows: list[CsvRow] = []
        for lead in leads:
            contact: ContactDocument | None = contacts.get(lead.contact_id)
            if is_erased(contact):
                continue

            rows.append(
                CsvRow(
                    cells=[
                        text_cell(lead.id),
                        moment_cell(lead.created_at, zone),
                        text_cell(lead.status),
                        text_cell(lead.lead_type),
                        text_cell(None if contact is None else contact.name),
                        text_cell(None if contact is None else contact.phone_number),
                        text_cell(lead.source_channel),
                        text_cell(lead.requested_date),
                        text_cell(lead.party_size),
                        text_cell(lead.budget),
                        text_cell(lead.details),
                        flag_cell(lead.is_sandbox),
                    ]
                )
            )

        return CsvExportPage(rows=rows, next_cursor=next_cursor)

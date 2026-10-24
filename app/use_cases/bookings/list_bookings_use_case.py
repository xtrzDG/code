from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.operations.bookings import BookingPage, ListBookingsQuery
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.shared.booking_listing import page_bookings
from app.use_cases.shared.business_access import require_business
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import load_time_zone

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class ListBookingsUseCase(UseCaseContract[ListBookingsQuery, BookingPage]):
    """
    One page of the bookings for the cabinet (concept /bookings), filtered by
    local start date range, status, resource and sandbox, ordered by start
    time (earliest first for upcoming lists, latest first for past ones):
    a keyset page the database reads, with only its contacts and booked
    services loaded (each booking shows its service and value).
    Shows customers' names and phones, so every call is written to the audit
    log as a view by the staff member.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ListBookingsQuery) -> BookingPage:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        resources: dict[ResourceId, ResourceDocument] = {
            resource.id: resource
            for resource in self._resource_repo.list_by_business(business.id)
        }
        bookings: list[BookingDocument]
        next_cursor: PageCursor | None
        bookings, next_cursor = page_bookings(
            self._booking_repo,
            business.id,
            zone,
            input_data.page,
            date_from_text=input_data.date_from,
            date_to_text=input_data.date_to,
            status=input_data.status,
            resource_id=input_data.resource_id,
            include_sandbox=input_data.include_sandbox,
            order=input_data.order,
        )
        contacts: dict[ContactId, ContactDocument] = self._contact_repo.get_many(
            business.id, [booking.contact_id for booking in bookings]
        )
        services: dict[KnowledgeItemId, KnowledgeItemDocument] = (
            self._knowledge_item_repo.get_many(
                business.id,
                [
                    booking.service_item_id
                    for booking in bookings
                    if booking.service_item_id is not None
                ],
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.actor_id,
                AuditAction.VIEW,
                BOOKING_ENTITY,
                None,
                now,
                input_data.client_ip_address,
            )
        )
        return BookingPage(
            items=[
                build_booking_view(
                    booking,
                    business.timezone,
                    zone,
                    resources.get(booking.resource_id),
                    contacts.get(booking.contact_id),
                    (
                        None
                        if booking.service_item_id is None
                        else services.get(booking.service_item_id)
                    ),
                )
                for booking in bookings
            ],
            next_cursor=next_cursor,
        )

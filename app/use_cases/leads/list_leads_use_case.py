from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import LeadRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.operations.leads import LeadPage, LeadStatusCount, ListLeadsQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.shared.business_access import require_business
from app.use_cases.shared.lead_views import build_lead_list_item
from app.use_cases.shared.operations_support import (
    build_audit_entry,
)
from app.utilities.paging.keyset_paging import finish_page, read_slice

LEAD_ENTITY: AuditEntityName = AuditEntityName("lead")


class ListLeadsUseCase(UseCaseContract[ListLeadsQuery, LeadPage]):
    """
    One page of the leads for the cabinet (concept /leads), newest first,
    with the contact's name and phone, and how many leads each status has
    (the status filter aside) for the tabs. The page is a keyset page read
    by the database and the counts are counted there, so neither grows with
    the years of leads. Every call is audited as a view of personal data.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        lead_repo: LeadRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ListLeadsQuery) -> LeadPage:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.actor_id,
                AuditAction.VIEW,
                LEAD_ENTITY,
                None,
                self._wall_clock.now_unix(),
            )
        )
        leads: list[LeadDocument]
        next_cursor: PageCursor | None
        leads, next_cursor = finish_page(
            self._lead_repo.page_by_business(
                business.id,
                read_slice(input_data.page),
                input_data.status,
                input_data.include_sandbox,
            ),
            input_data.page,
            sort_key=lambda lead: int(lead.created_at),
            item_id=lambda lead: str(lead.id),
        )
        contacts: dict[ContactId, ContactDocument] = self._contact_repo.get_many(
            business.id, [lead.contact_id for lead in leads]
        )
        counts: dict[LeadStatus, ListItemCount] = self._lead_repo.count_by_status(
            business.id, input_data.include_sandbox
        )
        return LeadPage(
            items=[
                build_lead_list_item(lead, contacts.get(lead.contact_id))
                for lead in leads
            ],
            next_cursor=next_cursor,
            status_counts=[
                LeadStatusCount(
                    status=status, count=counts.get(status, ListItemCount(0))
                )
                for status in LeadStatus
            ],
        )

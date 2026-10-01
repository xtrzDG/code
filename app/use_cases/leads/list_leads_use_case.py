from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    LeadRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.operations import LeadListView, ListLeadsQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.use_cases.bookings.operations_support import (
    build_audit_entry,
    require_business,
)
from app.use_cases.leads.lead_views import build_lead_list_item

LEAD_ENTITY: AuditEntityName = AuditEntityName("lead")


class ListLeadsUseCase(UseCaseContract[ListLeadsQuery, LeadListView]):
    """
    Leads for the cabinet (concept /leads), newest first, with the contact's
    name and phone; every call is audited as a view of personal data.
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

    def run(self, input_data: ListLeadsQuery) -> LeadListView:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        contacts: dict[ContactId, ContactDocument] = {
            contact.id: contact
            for contact in self._contact_repo.list_by_business(business.id)
        }
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
        return LeadListView(
            items=[
                build_lead_list_item(lead, contacts.get(lead.contact_id))
                for lead in self._lead_repo.list_by_business(business.id)
                if (input_data.include_sandbox or not lead.is_sandbox)
                and (input_data.status is None or lead.status is input_data.status)
            ]
        )

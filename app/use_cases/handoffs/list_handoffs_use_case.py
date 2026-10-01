from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    HandoffRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.operations import HandoffListView, ListHandoffsQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.use_cases.bookings.operations_support import (
    build_audit_entry,
    require_business,
)
from app.use_cases.handoffs.handoff_views import build_handoff_list_item

HANDOFF_ENTITY: AuditEntityName = AuditEntityName("handoff")


class ListHandoffsUseCase(UseCaseContract[ListHandoffsQuery, HandoffListView]):
    """
    Handoffs for the cabinet (concept /handoffs), newest first, with the
    contact to call back; every call is audited as a view of personal data.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        handoff_repo: HandoffRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ListHandoffsQuery) -> HandoffListView:
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
                HANDOFF_ENTITY,
                None,
                self._wall_clock.now_unix(),
            )
        )
        return HandoffListView(
            items=[
                build_handoff_list_item(handoff, contacts.get(handoff.contact_id))
                for handoff in self._handoff_repo.list_by_business(business.id)
                if (input_data.include_sandbox or not handoff.is_sandbox)
                and (input_data.status is None or handoff.status is input_data.status)
            ]
        )

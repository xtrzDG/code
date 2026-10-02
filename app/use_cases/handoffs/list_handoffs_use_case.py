from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.listing_filters import HandoffListFilter
from app.schemas.dto.operations.handoffs import HandoffPage, ListHandoffsQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.bookings.operations_support import (
    build_audit_entry,
    require_business,
)
from app.use_cases.handoffs.handoff_queue_paging import (
    handoff_sort_key,
    read_queue_page,
)
from app.use_cases.handoffs.handoff_views import build_handoff_list_item
from app.utilities.paging.keyset_paging import finish_page

HANDOFF_ENTITY: AuditEntityName = AuditEntityName("handoff")


class ListHandoffsUseCase(UseCaseContract[ListHandoffsQuery, HandoffPage]):
    """
    One page of the handoffs for the cabinet (concept /handoffs) with the
    contact to call back, and how many are open and resolved (the status
    filters aside) for the tabs.

    Open handoffs come first, the most urgent first, then the one waiting
    longest; resolved ones follow, the most recently resolved first
    (`handoff_queue_paging`: keyset pages per phase, read by the database).
    Every call is audited as a view of personal data.
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

    def run(self, input_data: ListHandoffsQuery) -> HandoffPage:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
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
        handoffs: list[HandoffDocument]
        next_cursor: PageCursor | None
        handoffs, next_cursor = finish_page(
            read_queue_page(
                self._handoff_repo,
                business.id,
                input_data.page,
                HandoffListFilter(
                    status=input_data.status,
                    include_sandbox=input_data.include_sandbox,
                ),
                input_data.is_open,
            ),
            input_data.page,
            sort_key=handoff_sort_key,
            item_id=lambda handoff: str(handoff.id),
        )
        contacts: dict[ContactId, ContactDocument] = self._contact_repo.get_many(
            business.id, [handoff.contact_id for handoff in handoffs]
        )
        counts: dict[HandoffStatus, ListItemCount] = self._handoff_repo.count_by_status(
            business.id, input_data.include_sandbox
        )
        resolved_count: int = int(counts.get(HandoffStatus.RESOLVED, 0))
        return HandoffPage(
            items=[
                build_handoff_list_item(handoff, contacts.get(handoff.contact_id))
                for handoff in handoffs
            ],
            next_cursor=next_cursor,
            open_count=ListItemCount(
                sum(int(count) for count in counts.values()) - resolved_count
            ),
            resolved_count=ListItemCount(resolved_count),
        )

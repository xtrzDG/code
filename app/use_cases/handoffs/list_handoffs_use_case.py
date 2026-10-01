from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    HandoffRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import HandoffStatus, HandoffUrgency
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.operations import HandoffPage, ListHandoffsQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.bookings.operations_support import (
    build_audit_entry,
    require_business,
)
from app.use_cases.handoffs.handoff_views import build_handoff_list_item
from app.utilities.paging.cursor_paging import take_page

HANDOFF_ENTITY: AuditEntityName = AuditEntityName("handoff")
# Sort-key bands (keys are compared descending): every open handoff above
# every resolved one, and within open ones a more urgent one above an older
# one. Timestamps in microseconds stay far below URGENCY_BAND.
OPEN_BAND: int = 10**19
URGENCY_BAND: int = 10**17
URGENCY_RANK: dict[HandoffUrgency, int] = {
    HandoffUrgency.LOW: 0,
    HandoffUrgency.NORMAL: 1,
    HandoffUrgency.HIGH: 2,
    HandoffUrgency.CRITICAL: 3,
}


class ListHandoffsUseCase(UseCaseContract[ListHandoffsQuery, HandoffPage]):
    """
    One page of the handoffs for the cabinet (concept /handoffs) with the
    contact to call back, and how many are open and resolved (the status
    filters aside) for the tabs.

    Open handoffs come first, the most urgent first, then the one waiting
    longest; resolved ones follow, the most recently resolved first. Every
    call is audited as a view of personal data.
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
        visible: list[HandoffDocument] = [
            handoff
            for handoff in self._handoff_repo.list_by_business(business.id)
            if input_data.include_sandbox or not handoff.is_sandbox
        ]
        handoffs: list[HandoffDocument]
        next_cursor: PageCursor | None
        handoffs, next_cursor = take_page(
            [
                handoff
                for handoff in visible
                if (input_data.status is None or handoff.status is input_data.status)
                and (
                    input_data.is_open is None or is_open(handoff) is input_data.is_open
                )
            ],
            input_data.page,
            sort_key=handoff_sort_key,
            item_id=lambda handoff: str(handoff.id),
        )
        open_count: int = sum(1 for handoff in visible if is_open(handoff))
        return HandoffPage(
            items=[
                build_handoff_list_item(handoff, contacts.get(handoff.contact_id))
                for handoff in handoffs
            ],
            next_cursor=next_cursor,
            open_count=ListItemCount(open_count),
            resolved_count=ListItemCount(len(visible) - open_count),
        )


def is_open(handoff: HandoffDocument) -> bool:
    """A handoff waits for a person until staff resolve it."""

    return handoff.status is not HandoffStatus.RESOLVED


def handoff_sort_key(handoff: HandoffDocument) -> int:
    """Open first (most urgent, then oldest), then latest resolved first."""

    if is_open(handoff):
        return (
            OPEN_BAND
            + URGENCY_RANK[handoff.urgency] * URGENCY_BAND
            - int(handoff.created_at)
        )

    return int(handoff.resolved_at or handoff.created_at)

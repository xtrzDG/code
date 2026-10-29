from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.waitlist import WaitlistEndReason, WaitlistStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.growth.waitlist_views import RemoveWaitlistEntryCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.shared.operations_support import build_audit_entry
from app.use_cases.waitlist.list_waitlist_use_case import WAITLIST_ENTRY_ENTITY
from app.use_cases.waitlist.waitlist_release import queue_next_offer

OPEN_STATUSES: frozenset[WaitlistStatus] = frozenset(
    {WaitlistStatus.WAITING, WaitlistStatus.OFFERED}
)


class RemoveWaitlistEntryUseCase(UseCaseContract[RemoveWaitlistEntryCommand, None]):
    """
    Staff take a customer off the waitlist (they booked by phone, or asked
    to): the entry ends (EXPIRED, removed, by whom), a place held for them
    goes to the next customer who fits, and the change is audited. Removing
    an entry that is over already changes nothing; a foreign or unknown one
    is not found.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        waitlist_entry_repo: WaitlistEntryRepoContract,
        audit_log_repo: AuditLogRepoContract,
        job_queue: JobQueueFacilitatorContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RemoveWaitlistEntryCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        entry: WaitlistEntryDocument | None = self._entry_repo.get(
            business.id, input_data.entry_id
        )
        if entry is None or entry.is_sandbox:
            raise NotFoundError(f"Waitlist entry {input_data.entry_id} was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        was_offered: bool = entry.status is WaitlistStatus.OFFERED

        def remove(current: WaitlistEntryDocument) -> WaitlistEntryDocument | None:
            if current.status not in OPEN_STATUSES:
                return None

            current.status = WaitlistStatus.EXPIRED
            current.end_reason = WaitlistEndReason.REMOVED
            current.offer_expires_at = None
            current.ended_at = now
            current.ended_by = input_data.user_id
            current.updated_at = now
            return current

        removed = self._entry_repo.update(business.id, entry.id, remove)
        if removed is None:
            return

        if was_offered:
            queue_next_offer(self._job_queue, removed, now)

        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.DELETE,
                WAITLIST_ENTRY_ENTITY,
                str(entry.id),
                now,
                input_data.client_ip_address,
            )
        )
        self._live_events.publish(
            business.id, LiveEventKind.WAITLIST_CHANGED, (entry.id,)
        )

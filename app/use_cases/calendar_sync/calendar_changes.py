"""
What every change of a resource's calendars shares: the resource and its
settings document, the audit entry with the owner who changed them, the
busy times of a source no longer linked forgotten, and the read right after
(each source within 2 s) whose outcome the answer shows.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.calendar_sync import (
    BusyTimeSyncFacilitatorContract,
    CalendarLinkChange,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.resource_calendar import ResourceCalendarView
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.calendar_sync.resource_calendar_reader import (
    ResourceCalendarReader,
)
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.calendar_sync.busy_windows import ON_DEMAND_READ_SECONDS
from app.utilities.calendar_sync.calendar_sync_keys import (
    busy_times_id_of,
    resource_calendar_link_id_of,
)

CALENDAR_ENTITY: AuditEntityName = AuditEntityName("resource_calendar")
MICROSECONDS_PER_SECOND: int = 1_000_000


@dataclass(frozen=True)
class CalendarChanges:
    """The shared steps of the calendar changes (module docstring)."""

    reader: ResourceCalendarReader
    busy_time_sync: BusyTimeSyncFacilitatorContract
    audit_log_repo: AuditLogRepoContract

    def change(
        self, resource: ResourceDocument, change: CalendarLinkChange, now: Microseconds
    ) -> ResourceCalendarLinkDocument | None:
        """Apply `change` to the resource's settings (made first if missing)."""

        self.reader.link_repo.add(
            ResourceCalendarLinkDocument(
                id=resource_calendar_link_id_of(resource.id),
                business_id=resource.business_id,
                resource_id=resource.id,
                created_at=now,
                updated_at=now,
            )
        )
        return self.reader.link_repo.update(resource.business_id, resource.id, change)

    def forget(
        self,
        resource: ResourceDocument,
        source: BusyTimeSource,
        feed_id: IcalImportFeedId | None = None,
    ) -> None:
        self.reader.busy_times_repo.delete(
            resource.business_id, [str(busy_times_id_of(resource.id, source, feed_id))]
        )

    def audit(
        self,
        resource: ResourceDocument,
        actor_id: UserId,
        action: AuditAction,
        now: Microseconds,
    ) -> None:
        self.audit_log_repo.append(
            build_audit_entry(
                resource.business_id,
                actor_id,
                action,
                CALENDAR_ENTITY,
                str(resource.id),
                now,
            )
        )

    def synced_view(self, resource: ResourceDocument) -> ResourceCalendarView:
        """Read the resource's sources now, then show its calendars."""

        self.busy_time_sync.sync_resource(resource, ON_DEMAND_READ_SECONDS)
        return self.reader.view_of(resource)


def due_now(link: ResourceCalendarLinkDocument, now: Microseconds) -> None:
    """Mark the settings due, so the sync job reads them at its next run."""

    link.next_sync_at = now
    link.updated_at = now

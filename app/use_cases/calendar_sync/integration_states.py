"""How each integration stands, summed over the resources that use it."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import IntegrationKind, IntegrationState
from app.schemas.domain.calendar_sync import (
    BusySourceStatus,
    ResourceCalendarLinkDocument,
)
from app.schemas.dto.calendar_sync.integrations import (
    IntegrationView,
    ResourceSyncSummary,
)
from app.schemas.typings.calendar_sync.constrained_integers import (
    LinkedResourceCount,
    LinkedSourceCount,
)


def integration_view(
    kind: IntegrationKind,
    statuses_by_resource: Sequence[Sequence[BusySourceStatus]],
    extra_attention: bool = False,
    extra_synced_at: Microseconds | None = None,
) -> IntegrationView:
    """
    One integration from the statuses of each resource that uses it: on
    when a resource uses it, needing attention when one of their last reads
    failed (or `extra_attention`, the integration's own failure).
    """

    attention: int = sum(
        1
        for statuses in statuses_by_resource
        if any(status.problem is not None for status in statuses)
    )
    synced: list[int] = [
        int(status.last_synced_at)
        for statuses in statuses_by_resource
        for status in statuses
        if status.last_synced_at is not None
    ]
    if extra_synced_at is not None:
        synced.append(int(extra_synced_at))
    is_on: bool = bool(statuses_by_resource) or extra_synced_at is not None
    return IntegrationView(
        kind=kind,
        state=(
            IntegrationState.ATTENTION
            if attention or extra_attention
            else IntegrationState.ON
            if is_on
            else IntegrationState.OFF
        ),
        resource_count=LinkedResourceCount(len(statuses_by_resource)),
        attention_count=LinkedResourceCount(attention),
        last_synced_at=Microseconds(max(synced)) if synced else None,
    )


def source_statuses(link: ResourceCalendarLinkDocument) -> list[BusySourceStatus]:
    """The status of every source that blocks the resource."""

    statuses: list[BusySourceStatus] = [feed.status for feed in link.ical_imports]
    if link.google_status is not None:
        statuses.insert(0, link.google_status)
    if link.booking_system is not None:
        statuses.append(link.booking_system.status)
    return statuses


def resource_summaries(
    links: Sequence[ResourceCalendarLinkDocument],
) -> list[ResourceSyncSummary]:
    """Each resource with a source or an export address, at a glance."""

    summaries: list[ResourceSyncSummary] = []
    for link in links:
        statuses: list[BusySourceStatus] = source_statuses(link)
        is_export_on: bool = link.ical_export_token_hash is not None
        if not statuses and not is_export_on:
            continue

        synced: list[int] = [
            int(status.last_synced_at)
            for status in statuses
            if status.last_synced_at is not None
        ]
        summaries.append(
            ResourceSyncSummary(
                resource_id=link.resource_id,
                source_count=LinkedSourceCount(len(statuses)),
                problem_count=LinkedSourceCount(
                    sum(1 for status in statuses if status.problem is not None)
                ),
                last_synced_at=Microseconds(max(synced)) if synced else None,
                is_export_on=is_export_on,
            )
        )
    return summaries

"""How each integration stands, summed over the resources that use it."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import IntegrationKind, IntegrationState
from app.schemas.domain.calendar_sync import BusySourceStatus
from app.schemas.dto.calendar_sync.integrations import IntegrationView
from app.schemas.typings.calendar_sync.constrained_integers import (
    LinkedResourceCount,
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

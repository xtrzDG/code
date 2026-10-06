"""Settings → Integrations: what a business connected, and how it goes."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import IntegrationKind, IntegrationState
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.calendar_sync.booleans import IsIcalExportOn
from app.schemas.typings.calendar_sync.constrained_integers import (
    LinkedResourceCount,
    LinkedSourceCount,
)


class IntegrationView(ImmutableDTO):
    """
    One integration: its state, how many resources use it (and how many of
    those need attention), and when it last synced anywhere.
    """

    kind: IntegrationKind
    state: IntegrationState
    resource_count: LinkedResourceCount = LinkedResourceCount(0)
    attention_count: LinkedResourceCount = LinkedResourceCount(0)
    last_synced_at: Microseconds | None = None


class ResourceSyncSummary(ImmutableDTO):
    """
    One resource's calendars at a glance (the resources list shows it):
    how many sources block it, how many failed their last read, when one
    last synced, and whether its export address exists.
    """

    resource_id: ResourceId
    source_count: LinkedSourceCount
    problem_count: LinkedSourceCount
    last_synced_at: Microseconds | None = None
    is_export_on: IsIcalExportOn = False


class IntegrationList(ImmutableDTO):
    """
    Every integration the platform offers a business, in a fixed order, and
    each resource that has calendars (`resources`).
    """

    items: list[IntegrationView]
    resources: list[ResourceSyncSummary] = []

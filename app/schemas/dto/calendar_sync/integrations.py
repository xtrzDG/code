"""Settings → Integrations: what a business connected, and how it goes."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import IntegrationKind, IntegrationState
from app.schemas.typings.calendar_sync.constrained_integers import (
    LinkedResourceCount,
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


class IntegrationList(ImmutableDTO):
    """Every integration the platform offers a business, in a fixed order."""

    items: list[IntegrationView]

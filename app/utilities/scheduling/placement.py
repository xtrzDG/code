"""Where and when a booking goes."""

from typing import NamedTuple

from app.schemas.domain.resources import ResourceDocument


class Placement(NamedTuple):
    """Where and when a booking goes (UTC seconds)."""

    resource: ResourceDocument
    starts_at: int
    ends_at: int

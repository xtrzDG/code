"""
The public status page (GET /v1/platform/status): each component's level
now and over 90 days, from the platform alerts and the announcements the
platform team writes; the announcements themselves (the cabinet's
banner).
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    StatusComponent,
    StatusLevel,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform_status.booleans import IsAnnouncementScheduled
from app.schemas.typings.platform_status.constrained_strings import (
    AnnouncementText,
    StatusDay,
)
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId


class PlatformStatusQuery(ImmutableDTO):
    """`?language=` picks the announcements' translation (else English)."""

    language: LanguageTag | None = None


class StatusDayView(ImmutableDTO):
    """A day of a component's history and the worst level it had that day."""

    day: StatusDay
    level: StatusLevel


class ComponentStatusView(ImmutableDTO):
    """A component's level now and its last 90 days, oldest first."""

    component: StatusComponent
    level: StatusLevel
    history: list[StatusDayView]


class AnnouncementView(ImmutableDTO):
    """
    An announcement in one language: what the banner and the status page
    show. `is_scheduled` is planned maintenance that has not started yet.
    """

    id: AnnouncementId
    level: AnnouncementLevel
    components: list[StatusComponent]
    text: AnnouncementText
    language: LanguageTag
    starts_at: Microseconds
    expected_end_at: Microseconds | None = None
    resolved_at: Microseconds | None = None
    updated_at: Microseconds
    is_scheduled: IsAnnouncementScheduled = False


class PlatformStatusView(ImmutableDTO):
    """
    The platform as owners and their customers see it: the overall level
    (the worst component), each component, the announcements shown now
    and the ones resolved in the last 90 days, newest first. `checked_at`
    is the platform alerts' latest check (null before the first).
    """

    level: StatusLevel
    checked_at: Microseconds | None = None
    components: list[ComponentStatusView]
    announcements: list[AnnouncementView]
    past_announcements: list[AnnouncementView]

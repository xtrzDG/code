from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    AnnouncementStatus,
    StatusComponent,
    StatusLevel,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform_status.constrained_integers import (
    StatusCheckCount,
)
from app.schemas.typings.platform_status.constrained_strings import (
    AnnouncementText,
    StatusDay,
)
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.schemas.typings.users.prefixed_id import UserId


class AnnouncementMessage(PersistentDocument):
    """An announcement's text in one language (English always present)."""

    language: LanguageTag
    text: AnnouncementText


class PlatformAnnouncementDocument(BaseDocument):
    """
    What the platform team tells every owner about the platform (a
    platform collection): the banner over the cabinet and the notice on
    the public status page. Its level counts for the components it names
    from `starts_at` (planned maintenance starts later) until the team
    resolves it. Creating, changing and resolving it are audited.
    """

    id: AnnouncementId = Field(default_factory=AnnouncementId)
    level: AnnouncementLevel
    status: AnnouncementStatus = AnnouncementStatus.ACTIVE
    components: list[StatusComponent] = Field(default_factory=list[StatusComponent])
    messages: list[AnnouncementMessage] = Field(min_length=1)
    starts_at: Microseconds
    expected_end_at: Microseconds | None = None
    resolved_at: Microseconds | None = None
    created_by: UserId
    updated_by: UserId | None = None


class ComponentDayRecord(PersistentDocument):
    """
    One component on one day of the status history: the worst level it
    was recorded at and how many of the day's records found it degraded
    or down.
    """

    component: StatusComponent
    worst_level: StatusLevel
    check_count: StatusCheckCount = StatusCheckCount(0)
    degraded_count: StatusCheckCount = StatusCheckCount(0)
    outage_count: StatusCheckCount = StatusCheckCount(0)


class PlatformStatusDayDocument(BaseDocument):
    """
    One UTC day of the public status page's history (a platform
    collection, stored under the day): the `record_platform_status` job
    folds every component's level into it every few minutes. Ninety days
    are shown; old days stay (one small row a day).
    """

    day: StatusDay
    components: list[ComponentDayRecord] = Field(
        default_factory=list[ComponentDayRecord]
    )
